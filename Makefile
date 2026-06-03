build:
	docker build -t hybrid-opt:local .

run:
	docker run --rm -p 8080:8080 hybrid-opt:local

test:
	pytest -q

docker-push:
	docker build -t ghcr.io/beloved12-AI/rdashphdia-elp/hybrid-opt:latest .
	docker push ghcr.io/beloved12-AI/rdashphdia-elp/hybrid-opt:latest
