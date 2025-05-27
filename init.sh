#!/bin/bash

# Do not autogenerate revision by default
AUTOGENERATE=false

while [[ $# -gt 0 ]]; do
    case "$1" in
        --auto)
            AUTOGENERATE=true
            shift
            ;;
        *)
            echo "Unknown argument: $1"
            exit 1
            ;;
    esac
done

if ! alembic check && $AUTOGENERATE; then
    alembic revision --autogenerate
    alembic upgrade head
fi

python ./src/main.py