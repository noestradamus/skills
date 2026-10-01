FROM python:3.12-slim@sha256:f77ac9e44ae96ef2c90b8053ea08c31f8be030f824196b0ae4db6d462c84e51f
RUN pip install --no-cache-dir uv==0.11.13
WORKDIR /lab
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project --python /usr/local/bin/python
COPY src ./src
RUN uv sync --frozen --python /usr/local/bin/python
COPY tests ./tests
COPY examples ./examples
COPY scripts ./scripts
COPY references ./references
COPY SKILL.md ./SKILL.md
ENV PATH="/lab/.venv/bin:$PATH" MPLCONFIGDIR=/tmp/matplotlib OMP_NUM_THREADS=1
CMD ["neuroevo", "doctor"]
