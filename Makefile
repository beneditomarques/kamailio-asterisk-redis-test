up:
	docker-compose up -d 

stop:
	docker-compose stop

restart:
	docker-compose restart 

build-kamailio:
	make down
	DOCKER_BUILDKIT=0 docker-compose -f docker-compose.yml build --no-cache kamailio

build-asterisk:
	make down
	DOCKER_BUILDKIT=0 docker-compose -f docker-compose.yml build --no-cache asterisk1

build-listener:
	make down
	DOCKER_BUILDKIT=0 docker-compose -f docker-compose.yml build --no-cache listener1

bash-kamailio:
	docker-compose exec kamailio sh

bash-asterisk1:
	docker-compose exec asterisk1 bash

bash-asterisk2:
	docker-compose exec asterisk2 bash

bash-listener1:
	docker-compose exec listener1 bash

bash-listener2:
	docker-compose exec listener2 bash

bash-redis:
	docker-compose exec redis sh


down:
	docker-compose stop 
	docker-compose rm -f 

logs:
	docker-compose logs -f 

