#!/bin/bash

# Alessandro
curl -XPOST "http://localhost:9201/interact" --header "Content-Type: application/json" --data '{"prompt": "Ciao, mi chiamo Alessandro", "user_id": "00000000-0000-0000-0000-000000000001"}'
curl -XPOST "http://localhost:9201/interact" --header "Content-Type: application/json" --data '{"prompt": "Mi piacciono le bionde e formose", "user_id": "00000000-0000-0000-0000-000000000001"}'
curl -XPOST "http://localhost:9201/interact" --header "Content-Type: application/json" --data '{"prompt": "Preferisco le moto alle macchine, soprattutto le enduro", "user_id": "00000000-0000-0000-0000-000000000001"}'

# Mario
curl -XPOST "http://localhost:9201/interact" --header "Content-Type: application/json" --data '{"prompt": "Ciao, mi chiamo Mario", "user_id": "00000000-0000-0000-0000-000000000002"}'
curl -XPOST "http://localhost:9201/interact" --header "Content-Type: application/json" --data '{"prompt": "Mi piacciono le ragazze more e magroline", "user_id": "00000000-0000-0000-0000-000000000002"}'
curl -XPOST "http://localhost:9201/interact" --header "Content-Type: application/json" --data '{"prompt": "Preferisco le macchine alle moto, soprattutto quelle da rally", "user_id": "00000000-0000-0000-0000-000000000002"}'