create-cert:
    mkcert -cert-file cert/cert.pem -key-file cert/key.pem localhost 127.0.0.1 ::1 10.10.1.201
