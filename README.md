# kamailio-asterisk-redis-test

1. Fazer com que o kamailio publique as mudanças de estado no redis pub sub
2. Reconfigurar o listener para ler os novos estados NOTINUSE, INUSE, RINGING, etc
2. Salvar os estados dentro do redis para resync no startup dos asterisks
3. Configurar o listener para se relogar no asterisk automaticamente caso perca conexão e fazer resync dos estados
4. Criar um resync automático de tempos em tempos, buscando o que está no redis
5. Analisar como ficam os status nas filas


