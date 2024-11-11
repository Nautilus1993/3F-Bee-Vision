package main

import (
    "net"
    "log"
)

func main() {
    conn, err := net.DialUDP("udp", nil, &net.UDPAddr{
        IP:   net.ParseIP("127.0.0.1"),
        Port: 8080,
    })
    if err != nil {
        log.Fatal(err)
    }
    defer conn.Close()

    // Send data to the server
    // ...
}