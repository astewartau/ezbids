Bootstrap: docker
From: node:16
Stage: spython-base

%files
    . /app

%post
    mkdir -p /app/api
    cd /app
    npm install -g pm2 typescript tsc-watch
    npm install
    
    cd api/ && ./dev.sh # Do I need this eventually?

%environment
    export MONGO_CONNECTION_STRING=mongodb://mongodb:27017/ezbids
    export PORT=8082

%runscript
    # cd /app
    cd /app/api
    exec /bin/bash "$@"

%startscript
    # cd /app
    cd /app/api
    exec /bin/bash "$@"