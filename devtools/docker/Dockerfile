FROM molssi/mamba141

COPY ./torchani_step/data/seamm-torchani.yml /root/environment.yml

RUN mamba env update -n base -f /root/environment.yml

COPY ./torchani_step/SEAMM_TorchANI.py_template /opt/conda/bin/SEAMM_TorchANI.py
RUN chmod +x /opt/conda/bin/SEAMM_TorchANI.py

WORKDIR /home
CMD ["SEAMM_TorchANI.py", "input.json"]
