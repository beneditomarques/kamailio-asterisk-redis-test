# kamailio-asterisk-redis-test

1. Fazer com que o kamailio publique as mudanças de estado no redis pub sub
2. Reconfigurar o listener para ler os novos estados NOTINUSE, INUSE, RINGING, etc
2. Salvar os estados dentro do redis para resync no startup dos asterisks
3. Configurar o listener para se relogar no asterisk automaticamente caso perca conexão e fazer resync dos estados
4. Criar um resync automático de tempos em tempos, buscando o que está no redis
5. Analisar como ficam os status nas filas
6. Resolver inconsistência quando o ramal está em chamada e o asterisk onde a ligação está acontecendo restarta (kamailio não altera mais o estado do peer)



### Objetivo

Criar um ambiente onde seja possível manter sempre todas as ramificações de uma chamada (desvios, transferências, ligação entre ramais, etc)
no mesmo PBX.

1. Kamailio como sip proxy fazendo balanceamento de carga entre os asterisks
2. Kamailio como registrar server
3. Kamailio publica no redis pub/sub eventos "registered" e "not_registered" quando um ramal registra/desregistra usando KEMI.
4. O controle do status dos dispositivos foi mantido asterisk (UNKNOWN, NOT_INUSE, INUSE, BUSY, INVALID, UNAVAILABLE, RINGING, RINGINUSE, ONHOLD)
5. O serviço `listener.py` é responsável por replicar os estados para os asterisks (similar ao corosync).