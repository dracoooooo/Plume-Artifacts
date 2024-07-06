FROM ubuntu:22.04

WORKDIR /plume
SHELL ["/bin/bash", "-c"]

ENV DEBIAN_FRONTEND=noninteractive

RUN apt update
RUN apt install -y python3 python3-setuptools python3-pip curl openjdk-11-jdk build-essential cmake libgmp-dev zlib1g-dev git g++ libclang-dev unzip maven libgmpxx4ldbl wcstools wget vim

COPY . .

RUN curl -L -o History.zip https://github.com/dracoooooo/Plume-Artifacts/releases/download/0.1/History.zip \
    && unzip History.zip -d . \
    && rm History.zip

# build Cobra
WORKDIR /plume/Tools/CobraVerifier
RUN mvn install:install-file -Dfile=./monosat/monosat.jar -DgroupId=monosat -DartifactId=monosat -Dversion=1.4.0 -Dpackaging=jar -DgeneratePom=true
RUN chmod +x ./run.sh && ./run.sh build

# install lein
WORKDIR /usr/local/bin
RUN wget https://raw.githubusercontent.com/technomancy/leiningen/stable/bin/lein && chmod u+x lein

# build elle-0.1.6 and elle-0.1.9
WORKDIR /plume/Tools/elle-0.1.6
RUN lein deps && lein uberjar

WORKDIR /plume/Tools/elle-0.1.9
RUN lein deps && lein uberjar

# install cargo and rust
RUN curl https://sh.rustup.rs -sSf | sh -s -- -y
ENV PATH=/root/.cargo/bin:$PATH

# build dbcop
WORKDIR /plume/Tools/dbcop
RUN cargo build --release

# install MonoSAT for Viper
WORKDIR /plume/Tools/Viper/resources/monosat
RUN cmake -DPYTHON=ON .
RUN make -j && make install

# install Viper dependencies
WORKDIR /plume/Tools/Viper
RUN pip install --no-cache-dir --upgrade -U -r ./src/docker/requirements.txt

# install mono dependencies
WORKDIR /plume/Tools/mono
RUN pip install --no-cache-dir --upgrade -U -r ./requirements.txt

# install CausalC+ dependencies
WORKDIR /plume/Tools/datalog
RUN pip install --no-cache-dir --upgrade -U -r ./requirements.txt

# build PolySI
WORKDIR /plume/Tools/PolySI
RUN chmod +x ./gradlew && ./gradlew jar

# install dependencies for reproducing expriments
WORKDIR /plume/Reproduce
RUN pip install --no-cache-dir --upgrade -U -r ./requirements.txt
RUN chmod +x reproduce_table3.sh reproduce_table4.sh

# build Plume
WORKDIR /plume/Plume
RUN mvn package -DskipTests

WORKDIR /plume

CMD ["bash"]

