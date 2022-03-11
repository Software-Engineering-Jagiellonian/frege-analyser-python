.PHONY: build-dev

build-dev:
	DOCKER_BUILDKIT=1 docker build -t frege-python-analyzer-dev --target dev -f Dockerfile .