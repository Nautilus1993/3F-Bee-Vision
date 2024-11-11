package main

import (
    "net"
    "log"
)

func main() {
    addr := net.UDPAddr{
        Port: 8080,
        IP:   net.ParseIP("127.0.0.1"),
    }
    conn, err := net.ListenUDP("udp", &addr)
    if err != nil {
        log.Fatal(err)
    }
    defer conn.Close()

    buffer := make([]byte, 1024)

    for {
        n, addr, err := conn.ReadFromUDP(buffer)
        if err != nil {
            log.Print(err)
            continue
        }

        // Process the data
        // ...
    }
}