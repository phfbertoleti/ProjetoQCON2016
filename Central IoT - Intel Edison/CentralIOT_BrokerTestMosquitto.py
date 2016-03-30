"Central IoT - QCON SP 2016"

__author__ = 'Pedro Bertoleti <phfbertoleti@gmail.com>'
__copyright__ = 'Copyright (C) 2016 Pedro Bertoleti'
__version__ = '1.0'
__date__ = 'Feb 2016'
__license__ = 'MIT'

import sys
import time
try:
  import paho.mqtt.client as mqtt
  import mraa
  import serial
  import smtplib
  import binascii
  from binascii import hexlify
  import mraa
  import pyupm_i2clcd as lcd
  from random import randrange
  import base64
  import os
except ImportError, mod:
  print "%s not found" % (mod)
  sys.exit(7)

 
TempoEntreLeituraSensores = 3           #Tempo (em segundos) entre duas leituras de sensores
TimeoutConexao = 5                      #Timeout da conexao com broker
TopicoSubscriber = "QCON2016SPEnvia"   #topico usado para receber dados do websocket 
TopicoPublisher = "QCON2016SPRecebe"  #topico usado para enviar dados do websocket
EmailConsumoJaFoiEnviado = 0            #variavel de controle do envio de e-mail (alerta que a meta de consumo de agua foi excedida)
EstaEmCalibracao = 0                    #variavel que indica se a placa esta em modo de calibracao

#definicao dos frames enviados para o sistema bare-metal de agua
ComandoVersaoAgua = "0201510000"
RequisitaConsumoAcumuladoAgua = "02014C0000"  #opcode 'L', endereco 0x01
RequisitaVazaoInstantaneaAgua = "0201560000"  #opcode 'V', endereco 0x01
ResetConsumoAgua              = "0201520000"  #opcode 'R', endereco 0x01
IniciaCalibracaoAgua          = "0201450000"  #opcode 'E', endereco 0x01
FinalizaCalibracaoAgua        = "0201530000"  #opcode 'S', endereco 0x01

#definicao dos frames enviados para o sistema bare-metal de luminosidade
ComandoVersaoLuminosidade  = "0202560000" #opcode 'V', endereco 0x02
ComandoLeituraLuminosidade = "02024C0000" #opcode 'L', endereco 0x02

#definicao dos frames enviados para o sistema bare-metal de temperatura
ComandoVersaoTemperatura  = "0203560000"  #opcode 'V', endereco 0x03
ComandoLeituraTemperatura = "0203540000"  #opcode 'T', endereco 0x03

#definicao, configuracao e inicializacao de I/Os da placa
lcdDisplay = lcd.Jhd1313m1(0, 0x3E, 0x62)     #Configura e inicializa comunicacao com display LCD
											  #0x3E: endereco i2c do controlador LCD 
											  #0x62: endereco i2c do controlador responsavel pelo RGB 

#definicao de parametros da criptografia proprietaria
ChavePublica = "QCON2016QCON2016"   #Chave publica usada na encriptacao. Deve ser conhecida pelo client que fara a decriptacao



def on_message(client, userdata, msg):
	"""
		Callback - chamado quando alguma mensagem eh recebida
		Corresponde a parte do sistema que opera sob demanda.
	""" 
	global EmailConsumoJaFoiEnviado
	global EstaEmCalibracao

	#descriptografa bytes recebidos
	PayloadDescriptografado = DescriptografaString(str(msg.payload))
	
	#escreve na tela a mensagem recebida
	print("Topico: "+msg.topic+" - Mensagem recebida: "+PayloadDescriptografado) 
	
	#recebeu comando para resetar consumo acumulado
	if (PayloadDescriptografado == "ResetConsumoAgua"):
		#tenta resetar / zerar o consumo acumulado ate conseguir. As tentativas sao feitas em intervalos de 3 segundos.
		dados_lidos = EnviaComandoSerial(ResetConsumoAgua,"R")	
				
		#reinicia variavel que controla envio do email (alerta que a meta de consumo de agua foi excedida)
		EmailConsumoJaFoiEnviado = 0
		
		#le e envia informacoes do sistema bare-metal por MQTT para pagina de monitoramento
		EnviaInformacoes()
		return 0
		
	if (PayloadDescriptografado == "IniciaCalibracaoAgua"):
		#tenta iniciar a calibracao ate conseguir. As tentativas sao feitas em intervalos de 3 segundos.
		dados_lidos = EnviaComandoSerial(IniciaCalibracaoAgua,"E")
		EstaEmCalibracao = 1
		print "--- Entrada no modo de calibracao ---"
		return 0
		
	if (PayloadDescriptografado == "FinalizaCalibracaoAgua"):
		#tenta finalizar a calibracao ate conseguir. As tentativas sao feitas em intervalos de 3 segundos.
		dados_lidos = EnviaComandoSerial(FinalizaCalibracaoAgua,"S")
		EstaEmCalibracao = 0
		print "--- Saida do modo de calibracao ---"
		EnviaInformacoes()
		return 0
	
    	
	if (PayloadDescriptografado == "RequisitaInformacoesAgua"):
		#le e envia informacoes do sistema bare-metal por MQTT para pagina de monitoramento
		EnviaInformacoes()
		return 0
	
	if ("EnviaConfigsMetaAgua" in PayloadDescriptografado):
		#meta de consumo e agua e e-mail para aviso foram recebidos. Sera feita a gravacao dos mesmos em arquivos-texto externos
		DadosConfigs = PayloadDescriptografado.split(">")
		GravaEmailEMeta(DadosConfigs[2], DadosConfigs[1])
		
		#reinicia variavel que controla envio do email (alerta que a meta de consumo de agua foi excedida)
		EmailConsumoJaFoiEnviado = 0


def CalculaChecksum(BytesRecebidos):
  """
     Funcao: Calcula checksum da mensagem recebida
     parametros: array de bytes a ser calculado checksum
     retorno: resposta do comando
  """
  
  CheckSumCalculado = 0    
  SomaCks = sum(BytesRecebidos)        
  CheckSumCalculado = ((~SomaCks) + 1)&0xFF
  return   CheckSumCalculado 

def EnviaComandoSerial(ComandoASerEnviado, OpcodeResposta):
	"""
		Funcao: Envia requisicao ate receber resposta
		parametros: Comando a ser enviado (string) 
					opcode que deve estar presente na resposta
		retorno: resposta do comando
	"""
	
	comando_bytes = ComandoASerEnviado.decode("hex")
	RecebeuResposta=0
		
	#tenta finalizar a calibracao ate conseguir. As tentativas sao feitas em intervalos de 3 segundos.
	while RecebeuResposta == 0:
		usart.write(comando_bytes)
		dados_lidos = usart.readline()
		
		#se ha o opcode esperado na resposta, trata-se de uma mensagem valida
		if (OpcodeResposta in dados_lidos):
			#obtem checksum recebido e tamanho recebido
			CksRecebidoStr = dados_lidos[4]
			HexCksRecebido = hexlify(CksRecebidoStr)
			CksRecebido = int (HexCksRecebido,16)
			TamanhoString = dados_lidos[3]
			hex = hexlify(TamanhoString)
			TamInt = int(hex, 16)
			DadosLidosBytes = bytearray()
			DadosLidosBytes.extend(dados_lidos[5:5+TamInt])		
		
			#verificacao do checksum	
			if (CalculaChecksum(DadosLidosBytes) == CksRecebido):
				RecebeuResposta = 1
				print "- Checksum do comando de opcode ",dados_lidos[1]," esta OK!"
			else:
				print "- Checksum Recebido: ",repr(CksRecebido)," Cks Calculado: ",CalculaChecksum(DadosLidosBytes)," Opcode: ",dados_lidos[1]
				print "Dados recebidos: "+repr(DadosLidosBytes)
		
	return dados_lidos
	
def EnviaEmailAvisoMetaAtingida():    
	"""
		Funcao: envia e-mail de aviso de meta de consumo atingido
		parametros: Meta configurada
		retorno: nenhum
	"""	
	global EmailConsumoJaFoiEnviado

	if (EmailConsumoJaFoiEnviado == 1):   #se o e-mail ja foi enviado, nada eh feito
		return 0

	#gravacao do e-mail em arquivo-texto externo
	arqEmail = open('email.txt', 'r')
	destinatario = arqEmail.readline()
	arqEmail.close()		
		
	#informacoes referentes ao e-mail	
	
	#IMPORTANTE: descomentar a linha abaixo e inserir o e-mail remetente desejado
	#remetente = ''	
	
	mensagem = "Aviso do sistema de monitoramento de Agua com IoT: seu consumo de agua excedeu a meta estabelecida. Consulte sua pagina de monitoramento."
	
	#IMPORTANTE: descomentar as linhas abaixo e inserir os dados de sua conta YahooMail
	#login = ''
	#senha = ''

	#envio do e-mail
	server = smtplib.SMTP('smtp.mail.yahoo.com', 587)
	server.starttls()
	server.login(login,senha)
	server.sendmail(remetente, destinatario, mensagem)
	server.quit()
	
	#sinlaiza que e-mail (alerta que a meta de consumo de agua foi excedida) ja foi enviado
	EmailConsumoJaFoiEnviado = 1

def LeMetaGravada():   
	"""
		Funcao: le a meta gravada no arquivo externo
		parametros: nenhum
		retorno: meta lida do arquivo externo
	""" 
	MetaLida=0
	
	try:
		#leitura (do arquivo texto) da meta estabelecida) e conversao do dado lido para float
		arqMeta = open('meta.txt', 'r')
		MetaLida = float(arqMeta.readline())
		arqMeta.close()		
	except  IOError:
		print "- Falha ao ler arquivo de meta"
	
	return MetaLida

def VerificaSeAtingiuMeta(ConsumoLido,MetaDeConsumo):    
	"""
		Funcao: verifica se a meta de consumo foi atingida e, se sim, dispara um e-mail ao usuario
		parametros: consumo lido
		retorno: "ok" - consumo acumulado abaixo da meta estabelecida
				"naook" - consumo acumulado acima da meta estabelecida
	""" 	
	StatusMeta="ok"
	
	try:
		ValorConsumoLido = float(ConsumoLido) 		

		print "Consumo usado na comparacao: ",repr(ConsumoLido)
		
		print "Meta lida: ",str(MetaDeConsumo)
		print "Consumo lido: ",ConsumoLido
		
		#verifica se consumo excedeu a meta
		if (ValorConsumoLido > MetaDeConsumo):
			StatusMeta="naook"
			
			#se a meta de consumo foi excedida, envia e-mail alertando o usuario
			EnviaEmailAvisoMetaAtingida()
	except  IOError:
		print "- Falha ao ler arquivo de meta"
	except ValueError:
		print "- Problemas ao converter leitura do consumo em float. Bytes recebidos: ",repr(ConsumoLido)
	
	return StatusMeta

	
def GravaEmailEMeta(EmailRecebido, MetaRecebida):
	"""
		Funcao: grava em um arquivo texto o e-mail e meta informados
		parametros: email e meta informados pela pagina de monitoramento
		retorno: nenhum
	""" 
	try:
		#gravacao do e-mail em arquivo-texto externo
		arqEmail = open('email.txt', 'w')
		arqEmail.write(EmailRecebido)
		arqEmail.close()
		
		print "- Arquivo de e-mail gravado com sucesso"
		
		#gravacao da meta em arquivo-texto externo
		arqMeta = open('meta.txt', 'w')
		arqMeta.write(MetaRecebida)
		arqMeta.close()
		
		print "- Arquivo de meta gravado com sucesso"
	except  IOError:
		print "- Falha ao gravar email e meta"
	
def DescriptografaString(DadoCriptografado):
	"""
		Funcao: descriptografa um dado informado
		parametros: dado (string)
		retorno: nenhum
	""" 
	
	StringCriptografada = base64.b64decode(DadoCriptografado)
	
	print "----String criptoigrafada: "+StringCriptografada
	
	StringCriptografadaBytes = bytearray(StringCriptografada)
	
	ChavePublicaBytes = bytearray(ChavePublica)
	SomaChavePublica = sum(ChavePublicaBytes)
	
	StringDescriptografada = bytearray(len(StringCriptografada))
	i=0
	
	for c in StringCriptografadaBytes: 
		StringDescriptografada[i] = (c - SomaChavePublica) & (0xFF)
		i=i+1
	
	print "Bytes descritpografados: ",StringDescriptografada
	return StringDescriptografada
	

	
def CriptografaString(StringParaCriptografar):
	"""
		Funcao: criptografa um dado informado (com criptografia proprietaria)
		parametros: dado (string)
		retorno: string criptografada
	""" 
	
	
	StringBytes = bytearray(StringParaCriptografar)
	ChavePublicaBytes = bytearray(ChavePublica)
	SomaChavePublica = sum(ChavePublicaBytes)
	
	StringCriptografada = bytearray(len(StringParaCriptografar))
	i=0
	
	for c in StringBytes: 
		StringCriptografada[i] = (c + SomaChavePublica) & (0xFF)
		i=i+1
	
	print "Bytes critpografados: ",StringCriptografada
	StringBase64 = base64.b64encode(StringCriptografada)
	print "Bytes codificados em base64: "+StringBase64
	return StringBase64

	
def EnviaInformacoes():
	"""
		Funcao: requisita informacoes ao sistema bare-metal de consumo de agua e as envia, por mqtt, a pagina de monitoramento
		parametros: nenhum
		retorno: nenhum
	""" 
	global EstaEmCalibracao

	#se esta em modo de calibracao, nao ha porque solicitar informacoes da placa
	#pois as informacoes relativas a medicao de agua estarao inconsistentes nessa
	#situacao.
	if (EstaEmCalibracao == 1):
		return 0

	#---------------------------------------
	#   PROTOCOLO  - RESPOSTA DAS PLACAS
	#---------------------------------------
	#                    [STX] [ENDERECO] [OPCODE] [TAMANHO] [DADOS]
	# POSICAO DO BYTE:    1       2         3          4        5
		
	#-------------------------------------
    #   REQUISICAO DAS INFORMACOES DO
    # MEDIDOR DE CONSUMO E FLUXO DE AGUA	
	#-------------------------------------	
		
	#requisita versao de firmware - medidor de consumo de agua	
	#tenta ler a versao do firmware ate conseguir. As leituras sao feitas em intervalos de 1 segundo.
	dados_lidos = EnviaComandoSerial(ComandoVersaoAgua,"Q")
	
	#"Filtra" versao de firmware da string recebida - medidor de consumo de agua
	VersaoStringAgua = dados_lidos[5:10]
	
	#requisita consumo acumulado - medidor de consumo de agua
	#Obs: tenta ler o consumo acumulado ate conseguir. As leituras sao feitas em intervalos de 1 segundo.
	dados_lidos = EnviaComandoSerial(RequisitaConsumoAcumuladoAgua,"L")
	
	#"Filtra" a string do consumo acumulado - medidor de consumo de agua
	ConsumoAcumuladoStringAgua = dados_lidos[5:11]

	#requisita vazao instantanea - medidor de consumo de agua
	#tenta ler a vazao instantanea ate conseguir. As leituras sao feitas em intervalos de 1 segundo.
	dados_lidos = EnviaComandoSerial(RequisitaVazaoInstantaneaAgua,"V")
	
	#"Filtra" a string da vazao instantanea - medidor de consumo de agua
	VazaoStringAgua = dados_lidos[5:11]

	#Le a meta de consumo / periodo gravada do arquivo texto - medidor de consumo de agua
	MetaConfiguradaAgua = LeMetaGravada()

	#verifica se meta de consumo foi atingida / excedida - medidor de consumo de agua
	StatusMetaAgua = VerificaSeAtingiuMeta(ConsumoAcumuladoStringAgua,MetaConfiguradaAgua)
	
	#-------------------------------------
    #   REQUISICAO DAS INFORMACOES DO
    #      MEDIDOR DE LUMINOSIDADE	
	#-------------------------------------	
	
	#requisita versao de firmware - medidor de luminosidade
	#tenta ler a versao do firmware ate conseguir. As leituras sao feitas em intervalos de 1 segundo.
	dados_lidos = EnviaComandoSerial(ComandoVersaoLuminosidade,"V")
	
	#"Filtra" versao de firmware da string recebida - medidor de luminosidade
	VersaoStringLuminosidade = dados_lidos[5:10]
	
	#requisita luminosidade - medidor de luminosidade
	#Obs: tenta ler a luminosidade ate conseguir. As leituras sao feitas em intervalos de 1 segundo.
	dados_lidos = EnviaComandoSerial(ComandoLeituraLuminosidade,"L")
	
	#"Filtra" a string do consumo acumulado - medidor de luminosidade
	StringLuminosidade = dados_lidos[5:8]
	
	#-------------------------------------
    #   REQUISICAO DAS INFORMACOES DO
    #      MEDIDOR DE TEMPERATURA	
	#-------------------------------------	
	
	#requisita versao de firmware - medidor de temperatura
	#tenta ler a versao do firmware ate conseguir. As leituras sao feitas em intervalos de 1 segundo.
	dados_lidos = EnviaComandoSerial(ComandoVersaoTemperatura,"V")
	
	#"Filtra" versao de firmware da string recebida - medidor de temperatura
	VersaoStringTemperatura = dados_lidos[5:10]
	
	#requisita luminosidade - medidor de temperatura
	#Obs: tenta ler a luminosidade ate conseguir. As leituras sao feitas em intervalos de 1 segundo.
	dados_lidos = EnviaComandoSerial(ComandoLeituraTemperatura,"T")
	
	#"Filtra" a string do consumo acumulado - medidor de temperatura
	StringTemperatura = dados_lidos[5:8]
	
	
	#monta string (nao criptografada) da leitura das informacoes
	#1) informacoes do leitor de agua
	StringInformacoesLidas = VersaoStringAgua+">"+ConsumoAcumuladoStringAgua+">"+VazaoStringAgua+">"+str(MetaConfiguradaAgua)+">"+StatusMetaAgua+">"
	
	#2) informacoes do leitor de luminosidade 
	StringInformacoesLidas = StringInformacoesLidas + VersaoStringLuminosidade+">"+StringLuminosidade+">"
	
	#2) informacoes do leitor de temperatura 
	StringInformacoesLidas = StringInformacoesLidas + VersaoStringTemperatura+">"+StringTemperatura
		
	StringCriptografada = CriptografaString(StringInformacoesLidas);
	
	try:
		#gravacao do e-mail em arquivo-texto externo
		arqCrypto = open('crypto.txt', 'w')
		arqCrypto.write(StringCriptografada)
		arqCrypto.close()	
	except  IOError:
		print "- Falha ao gravar log de Crypto"
	
	#envia para o broker as informacoes lidas e criptografadas
	#client.publish(TopicoPublisher, StringInformacoesLidas)
	client.publish(TopicoPublisher, StringCriptografada)
	print "---> Informacoes publicadas no broker!"


def InicializaDisplay():
	"""
		Funcao: Inicializa display
		parametros: nenhum
		retorno: nenhum
	""" 
	global lcdDisplay	
	print "Chave publica: "+ChavePublica+" Tamanho: ",len(ChavePublica)
	
	lcdDisplay.clear()
	
	#configura luz de fundo do display com RGB(231,222,67), que equivale a cor azul claro
	lcdDisplay.setColor(153,217,234)
	lcdDisplay.setCursor(0, 0)
	lcdDisplay.write(" Demonstracao  ")
	
	lcdDisplay.setCursor(1, 0)
	lcdDisplay.write(" QCON SP 2016  ")


def on_connect(client, userdata, flags, rc):
	"""
		Callback  - chamada quando a conexao eh estabelecida
	""" 
	print("Conectado ao broker. Retorno da conexao: "+str(rc))
 
	# Informa que o topico que este subscriber ira escutar
	client.subscribe(TopicoSubscriber)
	
#---------------------------		
#   Programa principal
#---------------------------
#configuracao da serial (FTDI): 9600 bauds, 8 bits, sem paridade e 1 stop-bit
 
port = "/dev/ttyUSB0"   
usart = serial.Serial (port,9600,serial.EIGHTBITS,serial.PARITY_NONE,serial.STOPBITS_ONE, 1)
	
client = mqtt.Client()
client.on_connect = on_connect   #configura callback (de quando eh estabelecida a conexao)
client.on_message = on_message   #configura callback (de quando eh recebida uma mensagem)
 
# tenta se conectar ao broker na porta 1883 (o parametro '60' eh o tempo de keepalive). 
# Nesse caso, se nenhuma mensagem for trafegada em ate 60 segundos, eh enviado um ping ao 
# broker de tempos em tempos (para manter a conexao ativa)
client.connect("test.mosquitto.org", 1883, 60)  

#loop infinito. Gerencia conexao periodicamente e executa demais tarefas necessarias
StatusConexaoBroker=0
TempoInicialSegundos=int(time.time())
TempoAtualSegundos=0

InicializaDisplay()
	
#-------------------------------------------------------------------------
#   Laco principal do sistema. Corresponde a parte continua do sistema
#-------------------------------------------------------------------------
while True:
	StatusConexaoBroker = client.loop(TimeoutConexao)

	if (StatusConexaoBroker > 0):
		client.connect("test.mosquitto.org", 1883, 60)  #se ocorrer algum erro, reconecta-se ao broker
  
	TempoAtualSegundos = int(time.time())
	
	#verifica se chegou o momento de executar o envio das informacoes para a pagina de monitoramento
	if ((TempoAtualSegundos-TempoInicialSegundos) > TempoEntreLeituraSensores):
		#reinicia a contagem de tempo
		TempoInicialSegundos = TempoAtualSegundos
		
		#le e envia informacoes do sistema bare-metal por MQTT para pagina de monitoramento
		EnviaInformacoes()