FROM allennlp/allennlp:v0.9.0

RUN pip install --upgrade pip

COPY ./src ./src
RUN src/setup.sh
ENV PYTHONPATH=DRS_parsing/:DRS_parsing/evaluation/:$PYTHONPATH
#RUN src/unit_tests.sh  # Takes too long

# Install custom version of AllenNLP
RUN git clone https://github.com/RikVN/allennlp
RUN git -C allennlp checkout DRS
RUN pip install -e ./allennlp

# Download GLoVe embeddings
RUN mkdir -p emb && wget "http://www.let.rug.nl/rikvannoord/embeddings/glove_pmb.zip" && unzip glove_pmb.zip -d emb && rm glove_pmb.zip

COPY . .

ENTRYPOINT ["/bin/bash"]
