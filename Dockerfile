FROM jcdemo/flaskapp
COPY ./ /opt/py
WORKDIR /opt/py
ENTRYPOINT python -u /opt/py/pytest.py
CMD python -u /opt/py/pytest.py
