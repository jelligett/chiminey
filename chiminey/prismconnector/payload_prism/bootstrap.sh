#!/bin/sh
# version 2.0


WORK_DIR=`pwd`

# Install Java
ext="tar.gz"
jdk_version=8

# how to get the latest oracle java version ref: https://gist.github.com/n0ts/40dd9bd45578556f93e7
cd /opt/
readonly url="http://www.oracle.com"
readonly jdk_download_url1="$url/technetwork/java/javase/downloads/index.html"
readonly jdk_download_url2=$(curl -s $jdk_download_url1 | egrep -o "\/technetwork\/java/\javase\/downloads\/jdk${jdk_version}-downloads-.+?\.html" | head -1 | cut -d '"' -f 1)
[[ -z "$jdk_download_url2" ]] && error "Could not get jdk download url - $jdk_download_url1"

readonly jdk_download_url3="${url}${jdk_download_url2}"
readonly jdk_download_url4=$(curl -s $jdk_download_url3 | egrep -o "http\:\/\/download.oracle\.com\/otn-pub\/java\/jdk\/[7-8]u[0-9]+\-(.*)+\/jdk-[7-8]u[0-9]+(.*)linux-x64.$ext")

for dl_url in ${jdk_download_url4[@]}; do
    wget --no-cookies \
         --no-check-certificate \
         --header "Cookie: oraclelicense=accept-securebackup-cookie" \
         -N $dl_url
done
JAVA_TARBALL=$(basename $dl_url)
tar xzfv $JAVA_TARBALL

# Install PRISM
PRISM_VERSION=4.3.1
PRISM_DOWNLOAD_URL=http://www.prismmodelchecker.org/dl/prism-${PRISM_VERSION}-linux64.tar.gz

yum -y update
yum -y install glibc.i686 libstdc++.so.6 gcc make

cd /opt/
curl -O ${PRISM_DOWNLOAD_URL}
tar xzvf prism-${PRISM_VERSION}-linux64.tar.gz
cd prism-${PRISM_VERSION}-linux64 && ./install.sh
chown -R root:root /opt/prism-${PRISM_VERSION}-linux64
chmod -R 755 /opt/prism-${PRISM_VERSION}-linux64

export PATH=/opt/prism-${PRISM_VERSION}-linux64/bin:$PATH

cd $WORK_DIR
