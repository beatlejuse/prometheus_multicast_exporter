#! /usr/bin/python
from flask import Flask, request
from threading import Thread, RLock
import select, socket, time, getopt, sys, os, html
app = Flask(__name__)
lock = RLock()
epoll = select.epoll()
s = 0
conn = {}
ip_to_fileno = {} # {'fileno':'ip',}
cache = {} # {'ip':[data_tmp,data,time_data_update,time_last_request],}
port = os.environ.get('SERVICE_PORT', 8000)
intf = os.environ.get('SERVICE_INTERFACE', 'a')
try:
    socket.inet_aton(intf)
except socket.error:
    print(intf + ' is not a valid ip (env SERVICE_INTERFACE)')
    sys.exit()
#
class PollThread(Thread):
    def __init__(self):
        Thread.__init__(self)
    def run(self):
        keyf = []
        while True:
            # если ключ не запрашивался более 15 минут
            pairs = [pair for pair in ip_to_fileno.items() if cache[pair[1]][3] + 900 <= time.time()]
            for p in pairs:
                # разрегистрировать подписки
                epoll.unregister(p[0])
                conn[p[0]].close()
                # удаляем запись в кэше
                lock.acquire()
                del conn[p[0]]
                cache.pop(p[1])
                ip_to_fileno.pop(p[0])
                lock.release()
            # получаем данные и сохраняем в кэш
            events = epoll.poll(1)
            for fileno, event in events:
                if event & select.EPOLLIN:
                    if cache[ip_to_fileno[fileno]][2] + 1 < time.time():
                        lock.acquire()
                        cache[ip_to_fileno[fileno]][2] = time.time()
                        cache[ip_to_fileno[fileno]][1] = cache[ip_to_fileno[fileno]][0]
                        cache[ip_to_fileno[fileno]][0] = len(conn[fileno].recv(64000))
                        lock.release()
                    else:
                        lock.acquire()
                        cache[ip_to_fileno[fileno]][0] += len(conn[fileno].recv(64000))
                        lock.release()
            # time.sleep(0.5)
#
@app.route('/stats')
def show_post2():
    strin = 'CONNECTIONS: ' + '<br>' + '\n'
    for items in conn.items():
        strin += str(items[0]) + ' ' + html.escape(str(items[1])) + '<br>' + '\n'
    strin += 'CACHE: ' + '<br>' + '\n'
    for items in cache.items():
        strin += str(items) + '<br>' + '\n'
    return strin
#
@app.route('/')
def show_post():
    # на веб-сервер пришёл запрос
    arg = request.args['target'].split(':') # ['91.203.253.225', '239.195.1.7', '16007']
    if request.args['module'] == 'udp':
        # провера адреса на валидность
        try:
            socket.inet_aton(arg[0])
            src = arg[0]
        except socket.error:
            print(arg[0] + ' is not a valid ip')
            return 'probe_success -1'
        try:
            socket.inet_aton(arg[1])
            ip = arg[1]
        except socket.error:
            print(arg[1] + ' is not a valid ip')
            return 'probe_success -1'
        if arg[2].isdigit():
            if  0 < int(arg[2]) < 65535:
                port = arg[2]
            else:
                print(arg[2] + ' is not a valid port')
                return 'probe_success -1'
        else:
            print(arg[2] + ' is not a valid number')
            return 'probe_success -1'
        key = src + '.' + ip + '.' + port # ключ подписки
        if cache.get(key): # если в кэше есть такой ключ
            # обновляем метку времени запроса
            lock.acquire()
            cache[key][3] = time.time()
            lock.release()
            # если данные не просрочены - отдаём данные
            if cache[key][2] + 15 >= time.time():
                strres = cache[key][1]
            # если данные просрочены отдаём "0"
            else:
                strres = 0
        else: # если такого ключа нет
            # добавляем адрес в кэш и ставим метку времени запроса
            # + подписываемся на мультикаст
            row = [0,0,0,time.time()]
            if not hasattr(socket, 'IP_MULTICAST_TTL'):
              setattr(socket, 'IP_MULTICAST_TTL', 33)
            if not hasattr(socket, 'IP_ADD_SOURCE_MEMBERSHIP'):
              setattr(socket, 'IP_ADD_SOURCE_MEMBERSHIP', 39)
            imr = (socket.inet_pton(socket.AF_INET, ip) +
                 socket.inet_pton(socket.AF_INET, intf) +
                 socket.inet_pton(socket.AF_INET, src))
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
            s.setsockopt(socket.SOL_IP, socket.IP_ADD_SOURCE_MEMBERSHIP, imr)
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind((ip, int(port)))
            s.setblocking( 0)
            epoll.register(s.fileno(), select.EPOLLIN)
            lock.acquire()
            conn[s.fileno()] = s
            cache.update({key:row})
            ip_to_fileno.update({s.fileno():key})
            lock.release()
            # ждём 1 секунду
            time.sleep(1)
            # отдаём данные
            strres = cache[key][1]
    return 'probe_success ' + str(strres)
#
if __name__ == "__main__":
    polltr = PollThread()
    polltr.start()
    app.run(host='0.0.0.0', port=port)
