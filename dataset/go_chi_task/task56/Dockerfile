FROM golang:1.21-alpine

# Install system dependencies
RUN apk add --no-cache \
    git \
    curl \
    wget \
    bash

# Clone the repository and checkout the specific commit
WORKDIR /workspace
RUN git clone https://github.com/go-chi/chi.git repo && \
    cd repo && \
    git checkout 7f280968675bcc9f310008fc6b8abff0b923734c

# Set up Go environment
WORKDIR /workspace/repo
RUN go mod download

# Copy the runner script
COPY runner.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/runner.sh

ENTRYPOINT ["/usr/local/bin/runner.sh"]
