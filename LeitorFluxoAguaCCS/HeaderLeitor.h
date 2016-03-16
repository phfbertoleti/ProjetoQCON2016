//Header geral do leitor de fluxo de água (demonstração da palestra "Embedded Systems e IoT: do bare-metal à comunicação wireless segura", realizado no QCON 2016)
//Autor: Pedro Bertoleti
//Data: 02/2016

#define VERSAO             "V1.00"

#define ENDERECO_BAREMETAL 1

#define SIM               1
#define NAO               0

//defines gerais do protocolo
#define MAX_TAM_BUFFER    20
#define STX               0x02
#define CHECKSUM_OK       1
#define FALHA_CHECKSUM    0
#define RECEPCAO_OK       1
#define SEM_RECEPCAO      0

//defines dos estados
#define ESTADO_STX                   1
#define ESTADO_ENDERECO              2
#define ESTADO_OPCODE                3
#define ESTADO_TAMANHO               4
#define ESTADO_CHECKSUM              5
#define ESTADO_BUFFER                6

//defines dos opcodes do protocolo
#define OPCODE_RESET_CONSUMO         'R'
#define OPCODE_LEITURA_CONSUMO       'L'
#define OPCODE_LEITURA_VAZAO         'V'
#define OPCODE_LEITURA_VERSAO        'Q'
#define OPCODE_ENTRA_EM_CALIBRACAO   'E'
#define OPCODE_SAI_DA_CALIBRACAO     'S'

//defines vinculados ao salvamento do consumo acumulado na eeprom
#define ENDERECOCHAVE                        1  
#define TEMPO_SALVAMENTO_CONSUMO_SEGUNDOS    18000 //5h

//defines vinculados a calibração
#define ENDERECOCALIBRACAO                   64


//estruturas / typedefs
typedef struct
{	
    char Endereco;
	char Opcode;
	char TamanhoMensagem;						
	char CheckSum;					
	char Buffer[MAX_TAM_BUFFER];					
} TDadosProtocoloLeitorAgua;

//variáveis globais
long ContadorPulsos;
long FrequenciaCalculada;
float VazaoCalculada;
TDadosProtocoloLeitorAgua  DadosProtocoloLeitorAgua;
char IndiceBuffer;
volatile char EstadoSerial;
volatile char ContadorIntTimer;
char RecebeuBufferCompleto;
volatile char VazaoAscii[7];
float ConsumoCalculado;
char ConsumoAscii[7];
long TempoSalvamentoConsumo;
const char ChaveEEPROM[] = "PedroBertoleti2015"; 
char VersaoEquipamento[] = VERSAO; 
long PulsosPorLitro;   //contém o numero de pulsos do sensor equivalentes a 1l de água consumido
char DeveGravarConsumo;
volatile char EstaEmModoCalibracao;   //indica se equipamento está em modo de calibração