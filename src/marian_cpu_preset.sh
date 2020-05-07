yes | sudo apt update
yes | sudo apt install python3
yes | sudo apt upgrade python3
sudo apt update-alternatives --install /usr/bin/python python /usr/bin/python3.6 1
yes | sudo apt install python3-pip
yes | sudo apt-get install cmake git build-essential doxygen libgoogle-perftools-dev google-perftools libz-dev libboost-all-dev zlib1g-dev libprotobuf10 protobuf-compiler libprotobuf-dev openssl libssl-dev ant zip unzip
wget https://apt.repos.intel.com/intel-gpg-keys/GPG-PUB-KEY-INTEL-SW-PRODUCTS-2019.PUB
sudo apt-key add GPG-PUB-KEY-INTEL-SW-PRODUCTS-2019.PUB
sudo sh -c 'echo deb https://apt.repos.intel.com/mkl all main > /etc/apt/sources.list.d/intel-mkl.list'
sudo apt-get update
yes | sudo apt-get install intel-mkl-64bit-2019.4-070
git clone https://github.com/RikVN/Neural_DRS.git
chmod +x ./Neural_DRS/src/setup.sh
