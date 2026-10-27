# Proxy de salida del sandbox de codigo: Smokescreen (Stripe), hecho para frenar SSRF. Niega por default las
# IPs privadas, loopback, link-local y de metadata; deja pasar el resto (CONNECT para https).
FROM golang:1.25-alpine AS build
RUN go install github.com/stripe/smokescreen@v0.1.0

FROM alpine:3.22
COPY --from=build /go/bin/smokescreen /usr/local/bin/smokescreen
USER nobody
EXPOSE 4750
CMD ["smokescreen", "--listen-ip=0.0.0.0", "--listen-port=4750"]
