# Dockerfile for installing and supporting the supported langauges for
# execution. For each language, the official installation method was followed
# wherever possible.
FROM python:3.9-slim-buster
RUN apt-get update -y
RUN apt-get install -y build-essential git wget unzip zip
RUN if ! id 1000; then useradd -m -u 1000 babelcode; fi

# Installing Julia
RUN wget https://julialang-s3.julialang.org/bin/linux/x64/1.7/julia-1.7.3-linux-x86_64.tar.gz \
        && tar zxvf julia-1.7.3-linux-x86_64.tar.gz

ENV PATH="/julia-1.7.3/bin:$PATH"

# Installing Java
RUN apt-get install -y default-jre=2:1.11*

# Installing Go
RUN wget https://go.dev/dl/go1.19.linux-amd64.tar.gz
RUN tar -C /usr/local -xvf go1.19.linux-amd64.tar.gz
ENV PATH=$PATH:/usr/local/go/bin

# Installing Node and NPM. Use the NVM package manager to ensure specific node
# versions.
ENV NVM_DIR=/nvm
RUN mkdir -p "${NVM_DIR}"
ENV NODE_VERSION=16.13.0
RUN wget -qO- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.1/install.sh | bash
RUN . "${NVM_DIR}/nvm.sh" && nvm install ${NODE_VERSION}
RUN . "${NVM_DIR}/nvm.sh" && nvm use v${NODE_VERSION}
RUN . "${NVM_DIR}/nvm.sh" && nvm alias default v${NODE_VERSION}
ENV PATH="${NVM_DIR}/versions/node/v${NODE_VERSION}/bin/:${PATH}"


# # Installing Lua
RUN apt install -y lua5.3

# # Installing Kotlin
RUN wget https://github.com/JetBrains/kotlin/releases/download/v1.7.10/kotlin-compiler-1.7.10.zip
RUN unzip kotlin-compiler-1.7.10.zip
ENV PATH="/kotlinc/bin:$PATH"
RUN mkdir /kotlin_dir
ENV KONAN_DATA_DIR="/kotlin_dir"
RUN mkdir "${KONAN_DATA_DIR}}"
RUN chown -R 1000:root "$KONAN_DATA_DIR" && chmod -R 775 "$KONAN_DATA_DIR"
# Need to do this so it downloads necessary dependencies
RUN echo "fun main() {println(\"Hello Kotlin/Native!\")}" > code.kt 
RUN kotlinc code.kt -include-runtime -d test.jar
RUN rm code.kt

# Installing Rust
RUN wget https://static.rust-lang.org/dist/rust-1.64.0-x86_64-unknown-linux-gnu.tar.gz
RUN tar -xvf rust-1.64.0-x86_64-unknown-linux-gnu.tar.gz
RUN bash rust-1.64.0-x86_64-unknown-linux-gnu/install.sh

# Installing Haskell
RUN apt-get  -y install haskell-platform=2014.*

# Installing C#
RUN wget https://dot.net/v1/dotnet-install.sh
RUN chmod +x ./dotnet-install.sh
RUN ./dotnet-install.sh -c 6.0 --runtime aspnetcore
RUN apt-get install -y mono-complete

# Install PHP
RUN apt-get install -y php-cli

# Install Scala
RUN wget https://github.com/coursier/launchers/raw/master/cs-x86_64-pc-linux.gz 
RUN gzip -d cs-x86_64-pc-linux.gz && mv cs-x86_64-pc-linux cs && chmod +x cs && ./cs setup -y
RUN mv ~/.local/share/coursier /coursier
RUN chown -R 1000:root "/coursier" && chmod -R 775 "/coursier"
ENV PATH="$PATH:/coursier/bin"

# Install R
RUN apt-get install r-base -y

# Install dart
RUN wget https://storage.googleapis.com/dart-archive/channels/stable/release/2.18.5/linux_packages/dart_2.18.5-1_amd64.deb
RUN dpkg -i dart_2.18.5-1_amd64.deb
RUN apt-get install -f
RUN mv "/usr/lib/dart" "/dart"
RUN chown -R 1000:root "/dart" && chmod -R 775 "/dart"
ENV PATH="$PATH:/dart/bin"

# Installing python requirements.
COPY requirements.txt .
RUN pip --no-cache-dir install -r requirements.txt

RUN chown -R 1000:root "$NVM_DIR" && chmod -R 775 "$NVM_DIR"

# Copy the framework to the working directory.
RUN mkdir /evaluation
RUN chown -R 1000:root /evaluation && chmod -R 775 /evaluation
WORKDIR "/evaluation"
COPY package.json .

ENV NODE_PATH="/${NVM_DIR}/versions/node/v${NODE_VERSION}/lib/node_modules"
RUN npm install
RUN npm install --global --verbose typescript

# Need to do this for go otherwise there are permission denied errors.
ENV GOCACHE="/evaluation/.cache"

# Copy the framework to the working directory.
COPY . .
