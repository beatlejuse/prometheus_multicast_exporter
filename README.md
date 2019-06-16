# Multicast channel check + http metrics exporter

### How it works

- Exporter get source/ip/port from http request. Then add multicast subscription for 15 minutes.
- If during this time this multicast address is not requested, the subscription will be canceled.
- Then exporter listen multicast channel, collect messages and gives the size of the messages that came in 1 second.
- If in 15 seconds there were no messages in the channel, '0' is returned.
- if the request contains an invalid source/ip/port then returns '-1'.


### Run

- You can run metrics exporter by Docker-compose using the following docker-compose.yaml file

        version: "2"
        services:
          pytest:
            restart: always
            image: gitlab.itinvest.ru:5001/adm/multicast-exporter:1.0.0
            container_name: pytest
            mem_limit: 100m
            memswap_limit: 100m
            network_mode: "host"
            privileged: "true"
            environment:
              SERVICE_INTERFACE: '10.231.1.180'
              SERVICE_PORT: 8000 

###  Prometheus configuration
      - job_name: 'blackbox-udp'
        metrics_path: /
        params:
          module: [udp]
        static_configs:
          - targets:
            - 91.255.255.225:239.155.155.5:16007
            - 91.255.255.225:239.155.155.55:17007
            labels:
              proto: '<additional label>'
        relabel_configs:
          - source_labels: [__address__]
            target_label: __param_target
          - source_labels: [__param_target]
            target_label: instance
          - target_label: __address__
            replacement: <exporter ip>:<port>

### Statistics

- You can get multicast subscription statistics at ```http://<host>:<port>/stats```

### Debug

- You can add multicast subscription manually by next http request: ```http://<exporter_ip>:<exporter_port>/?module=udp&target=<channel_src>%3A<channel_ip>%3A<channel_port>```

