FROM golang:1.25-bookworm AS builder

WORKDIR /src

COPY go.mod go.sum ./
RUN go mod download

COPY . .

ENV CGO_ENABLED=1 GOOS=linux
RUN go build -o /out/whatsapp-bridge .

FROM debian:bookworm-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY --from=builder /out/whatsapp-bridge /app/whatsapp-bridge

ENV WHATSAPP_STORE_DIR=/app/store
ENV WHATSAPP_REST_PORT=8090

EXPOSE 8090

ENTRYPOINT ["/app/whatsapp-bridge"]
