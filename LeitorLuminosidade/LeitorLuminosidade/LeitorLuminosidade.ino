//Software do leitor de luminosidade (demonstração da palestra 
//"Embedded Systems e IoT: do bare-metal à comunicação wireless segura", 
//realizado no QCON 2016).
//Autor: Pedro Bertoleti
//Data: 02/2016
//
//IMPORTANTE: este software funciona tanto com shield ZigBEE
//            quanto com o ZigBEE ligado diretamente a serial


//----------------
// Defines gerais
//----------------
#define VERSAO               "V1.00"
#define TAMANHO_VERSAO       5
#define TAMANHO_LUMINOSIDADE 3
#define ENDERECO_BAREMETAL   2
#define SIM                  1
#define NAO                  0
#define DIA                  "DIA"
#define NOITE                "NOI"

//defines do protocolo
#define MAX_TAM_BUFFER    20
#define STX               0x02
#define CHECKSUM_OK       1
#define FALHA_CHECKSUM    0
#define RECEPCAO_OK       1
#define SEM_RECEPCAO      0

//defines dos estados
#define ESTADO_STX        1
#define ESTADO_ENDERECO   2
#define ESTADO_OPCODE     3
#define ESTADO_TAMANHO    4
#define ESTADO_CHECKSUM   5
#define ESTADO_BUFFER     6

//defines dos opcodes do protocolo (para sensor de luminosidade)
#define OPCODE_LEITURA_LUMINOSIDADE    'L'
#define OPCODE_VERSAO                  'V'

//define - tamanho da mensagem de resposta
#define TAMANHO_MAX_MSG_RESPOSTA        10 //8 bytes = STX (1 byte) + Endereço (1 byte) + Opcode (1 byte) + tamanho (1 byte) + checksum (1 byte) + Buffer (5 bytes)

//define - pino de leitura analógica
#define PINO_SENSOR_LUMINOSIDADE   0 //usa analog pin 0

//define - valor máximo que o ADC retorna na leitura
#define VALOR_MAX_ADC              1023

//----------------
// Estruturas / 
// typedefs
//----------------
typedef struct
{	
    char Endereco;
    char Opcode;
    char TamanhoMensagem;						
    char CheckSum;					
    char Buffer[MAX_TAM_BUFFER];					
} TDadosProtocoloLeitorLuminosidade;

//----------------
// variáveis globais
//----------------
TDadosProtocoloLeitorLuminosidade DadosProtocoloLeitorLuminosidade;
volatile char EstadoSerial;
char RecebeuBufferCompleto;
char DeveEnviarLuminosidade;
char DeveEnviarVersao;
char IndiceBuffer;

//----------------
// Prototypes
//----------------
void TrataMensagem(void);
void MontaEEnviaMensagem(char Opcode, char Tamanho, char * Dado);
void AguardaSTX();
void AguardaEndereco(char ByteRecebido);
void AguardaOpcode(char ByteRecebido);
void AguardaTamanho(char ByteRecebido);
void AguardaCheckSum(char ByteRecebido);
void AguardaBuffer(char ByteRecebido);
char CalculaCheckSum(void);
void MaquinaEstadoSerial(char ByteRecebido);
void EnviaLuminosidade(int LeituraADC);
void EnviaVersao(void);

//----------------
// Implementação /
//    funções
//----------------

//Aguarda STX - função da máquina de estados da comunicação serial
//parametros: byte recebido
//saida: nenhum
void AguardaSTX(char ByteRecebido)
{
    if (ByteRecebido == STX)
    {
	      memset(&DadosProtocoloLeitorLuminosidade, 0, sizeof(TDadosProtocoloLeitorLuminosidade));   //limpa dados do protocolo
	      EstadoSerial = ESTADO_ENDERECO;
    }
    else
	      EstadoSerial = ESTADO_STX;
}

//Aguarda endereço do destinatário da mensagem - função da máquina de estados da comunicação serial
//parametros: byte recebido
//saida: nenhum
void AguardaEndereco(char ByteRecebido)
{
    DadosProtocoloLeitorLuminosidade.Endereco = ByteRecebido;
	
    if (DadosProtocoloLeitorLuminosidade.Endereco == ENDERECO_BAREMETAL)
      	EstadoSerial = ESTADO_OPCODE;	
    else
	      EstadoSerial = ESTADO_STX;	
}

//Aguarda Opcode da mensagem - função da máquina de estados da comunicação serial
//parametros: byte recebido
//saida: nenhum
void AguardaOpcode(char ByteRecebido)
{
    DadosProtocoloLeitorLuminosidade.Opcode = ByteRecebido;
    EstadoSerial = ESTADO_TAMANHO;	
}

//Aguarda tamanho da mensagem - função da máquina de estados da comunicação serial
//parametros: byte recebido
//saida: nenhum
void AguardaTamanho(char ByteRecebido)
{
    if (ByteRecebido > MAX_TAM_BUFFER)
  	    EstadoSerial = ESTADO_STX;   //tamanho recebido é inválido (maior que o máximo permitido). A máquina de estados é resetada.
    else
    {	
      	DadosProtocoloLeitorLuminosidade.TamanhoMensagem = ByteRecebido;
	      EstadoSerial = ESTADO_CHECKSUM;	
    }
}

//Aguarda checksum da mensagem - função da máquina de estados da comunicação serial
//parametros: byte recebido
//saida: nenhum
void AguardaCheckSum(char ByteRecebido)
{	
    DadosProtocoloLeitorLuminosidade.CheckSum = ByteRecebido;
    
    if(DadosProtocoloLeitorLuminosidade.TamanhoMensagem > 0)
    {
        IndiceBuffer = 0;
	      EstadoSerial = ESTADO_BUFFER;
    }
    else
    {
       	RecebeuBufferCompleto = RECEPCAO_OK;
	      EstadoSerial = ESTADO_STX;
    }
}

//Aguarda buffer da mensagem - função da máquina de estados da comunicação serial
//parametros: byte recebido
//saida: nenhum
void AguardaBuffer(char ByteRecebido)
{
    if(IndiceBuffer < DadosProtocoloLeitorLuminosidade.TamanhoMensagem)
    {
	      DadosProtocoloLeitorLuminosidade.Buffer[IndiceBuffer] = ByteRecebido;
	      IndiceBuffer++;
    }
    else
    {
	      //buffer completo. Faz o tratamento da mensagem e reinicia máquina de estados
	      if (CalculaCheckSum() == CHECKSUM_OK)
            RecebeuBufferCompleto = RECEPCAO_OK;
	      else
            RecebeuBufferCompleto = SEM_RECEPCAO;
	
	      EstadoSerial = ESTADO_STX;
    }
}

//Função: checa o checksum da mensagem recebida pela UART
//parametros: nenhum
//saida: nenhum
char CalculaCheckSum(void)
{
    char CheckSumCalculado;
    char i;
	
    CheckSumCalculado = 0;
	
    for(i=0; i<DadosProtocoloLeitorLuminosidade.TamanhoMensagem; i++)
	      CheckSumCalculado = CheckSumCalculado + DadosProtocoloLeitorLuminosidade.Buffer[i];
		
    CheckSumCalculado = (~CheckSumCalculado) +1;
	
    if (CheckSumCalculado == DadosProtocoloLeitorLuminosidade.CheckSum)
	      return CHECKSUM_OK;
    else
	      return FALHA_CHECKSUM;
}


//Função que faz o gerenciamento dos estados da máquina de estado. É chamada sempre que um byte chega da serial
//parametros: byte recebido pela serial
//saida: nenhum
void MaquinaEstadoSerial(char ByteRecebido)
{
    switch(EstadoSerial)
    {
        case ESTADO_STX:
        {
            AguardaSTX(ByteRecebido);
            break; 
        }

	      case ESTADO_ENDERECO:
        {
            AguardaEndereco(ByteRecebido);
            break; 
        }
		
        case ESTADO_OPCODE:
        {
            AguardaOpcode(ByteRecebido);
            break; 
        }

        case ESTADO_TAMANHO:
        {
            AguardaTamanho(ByteRecebido);
            break; 
        }

        case ESTADO_CHECKSUM:
        {
            AguardaCheckSum(ByteRecebido);
            break; 
        }

        case ESTADO_BUFFER:
        {
            AguardaBuffer(ByteRecebido);
            break; 
        }

        
        default:   //se o estado tiver qualquer valro diferente dos esperados, significa que algo corrompeu seu valor (invasão de memória RAM). Logo a máquina de estados é reuniciada.
        {
            EstadoSerial=ESTADO_STX;
            RecebeuBufferCompleto = SEM_RECEPCAO;
            memset(&DadosProtocoloLeitorLuminosidade, 0, sizeof(TDadosProtocoloLeitorLuminosidade));   //limpa dados do protocolo
            break;
        }
    }
}

//Função: trata mensagem recebida pela UART
//parametros: nenhum
//saida: nenhum
void TrataMensagem(void)
{
    switch (DadosProtocoloLeitorLuminosidade.Opcode)
    {
        case OPCODE_LEITURA_LUMINOSIDADE:
        {
            DeveEnviarLuminosidade = SIM;
            break;
        }

        case OPCODE_VERSAO:
        {
            DeveEnviarVersao = SIM;
            break;
        }

        default:
        {
            DeveEnviarLuminosidade = NAO;
            DeveEnviarVersao = NAO;
            RecebeuBufferCompleto = SEM_RECEPCAO;
            EstadoSerial = ESTADO_STX;

            //limpa dados do protocolo 
            memset(&DadosProtocoloLeitorLuminosidade, 0, sizeof(TDadosProtocoloLeitorLuminosidade));  
        }
    }    
}

//Função: formata e envia a mensagem (em resposta à solicitação)
//parametros: opcode, tamanho, ponteiro pro dado ascii
//saida: nenhum
void MontaEEnviaMensagem(char Opcode, char Tamanho, char * Dado)
{
    char BufferAscii[TAMANHO_MAX_MSG_RESPOSTA];
    char CheckSumMsg;
    char i;

    CheckSumMsg = 0;

    //monta mensagem de resposta à solicitação de consumo
    memset(BufferAscii,0,TAMANHO_MAX_MSG_RESPOSTA);
    BufferAscii[0]=STX;
    BufferAscii[1]=ENDERECO_BAREMETAL;
    BufferAscii[2]=Opcode; 
    BufferAscii[3]=Tamanho; 

    if (Tamanho)
    {
        for(i=0; i<Tamanho; i++)
        {
            CheckSumMsg = CheckSumMsg + Dado[i];
            BufferAscii[5+i]=Dado[i];
        }
    }
    
    CheckSumMsg = (~CheckSumMsg) + 1;
    BufferAscii[4]=CheckSumMsg;

   //envio da mensagem
   for (i=0;i<sizeof(BufferAscii);i++)
      Serial.write(BufferAscii[i]);
} 

//Função: envia para a serial a luminosidade
//parametros: nenhum
//saida: nenhum
void EnviaLuminosidade(int LeituraADC)
{    
    int PorcentagemLuminosidade;
    char LeituraDia[]=DIA;
    char LeituraNoite[]=NOITE;
    
    PorcentagemLuminosidade = LeituraADC;

    if (PorcentagemLuminosidade < 375)
        MontaEEnviaMensagem(OPCODE_LEITURA_LUMINOSIDADE, TAMANHO_LUMINOSIDADE, (char *)LeituraNoite);   
    else
        MontaEEnviaMensagem(OPCODE_LEITURA_LUMINOSIDADE, TAMANHO_LUMINOSIDADE, (char *)LeituraDia); 

}

//Função: envia para a serial a versao do firmware
//parametros: nenhum
//saida: nenhum
void EnviaVersao(void)
{  
   char VersaoFW[]=VERSAO;

   MontaEEnviaMensagem(OPCODE_VERSAO, TAMANHO_VERSAO, (char *)VersaoFW);
}


void setup() 
{
    //inicializa variáveis de controle de envio de luminosidade
    RecebeuBufferCompleto = SEM_RECEPCAO;
    DeveEnviarLuminosidade = NAO;
    DeveEnviarVersao = NAO;
  
    //inicia comunicação serial a 9600 bauds 
    Serial.begin(9600);
}

void loop() 
{
    int LeituraADC;
    char ByteLido;

    if (Serial.available())
    {
        ByteLido = Serial.read();
        MaquinaEstadoSerial(ByteLido);
    }
        
    if (RecebeuBufferCompleto == RECEPCAO_OK)
    {
        TrataMensagem();
        RecebeuBufferCompleto = SEM_RECEPCAO;
    }
    
    if (DeveEnviarLuminosidade == SIM)    
    {
        LeituraADC = analogRead(PINO_SENSOR_LUMINOSIDADE);
        EnviaLuminosidade(LeituraADC);
        DeveEnviarLuminosidade = NAO; 
    }
    
    if (DeveEnviarVersao == SIM)    
    {
        EnviaVersao();
        DeveEnviarVersao = NAO; 
    }    
}
