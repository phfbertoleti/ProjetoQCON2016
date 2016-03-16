(function() {
	window.Main = {};
	Main.Page = (function() {
		var mosq = null;
		function Page() {
			var _this = this;
			mosq = new Mosquitto();

			$('#connect-button').click(function() {
				return _this.connect();
			});
			$('#disconnect-button').click(function() {
				return _this.disconnect();
			});
			$('#subscribe-button').click(function() {
				return _this.subscribe();
			});
			$('#unsubscribe-button').click(function() {
				return _this.unsubscribe();
			});
			
			
			$('#publish-envia-configs-meta').click(function() {
				return _this.EnviaConfigsMeta();
			});

			
			$('#publish-requisita-informacoes').click(function() {
				return _this.RequisitaInformacoes();
			});

			
			$('#publish-reset_consumo').click(function() {
				return _this.ResetConsumo();
			});			
			
			
			$('#publish-inicia-calibracao').click(function() {
				return _this.IniciaCalibracao();
			});	
			
			$('#publish-finaliza-calibracao').click(function() {
				return _this.FinalizaCalibracao();
			});	

			mosq.onconnect = function(rc){
				var p = document.createElement("p");
				var topic = $('#pub-subscribe-text')[0].value;
				p.innerHTML = "CONNACK " + rc;
				$("#debug").append(p);
				mosq.subscribe(topic, 0);
				
			};
			mosq.ondisconnect = function(rc){
				var p = document.createElement("p");
				var url = "ws://test.mosquitto.org:8080/mqtt";
				
				p.innerHTML = "Lost connection";
				$("#debug").append(p);				
				mosq.connect(url);
			};
			mosq.onmessage = function(topic, payload, qos){
				//Utiliza o Google  Code Crypto-JS para descriptografar
				var p = document.createElement("p");
				var SomaBytesChavePublica = 1012;
				var PayloadEmBytes = atob(payload);  
				var CodigoChar = 0;
				var CharDescriptografado=" ";
				var i=0;
				var StringDescriptografada = "";
				var TamanhoString = PayloadEmBytes.length;
				var BytesDescriptografados=[];
				
				for(i=0; i<TamanhoString; i++)
				{				
					CodigoChar = PayloadEmBytes.charCodeAt(i);	
					CharDescriptografado = ((CodigoChar-SomaBytesChavePublica) & 0xFF);
					StringDescriptografada = StringDescriptografada + String.fromCharCode(CharDescriptografado);
				}
				
				var payload_parseado = StringDescriptografada.split(">");				
				
				p.innerHTML = " <table width='100%' border=0><tr><th><table width='100%' border=0><tr><th  width='20%'>Versão do firmware(medidor de consumo de água):<br>"+payload_parseado[0]+"<br><img src='firmware.jpg'></th><th  width='20%'>Consumo acumulado: "+payload_parseado[1]+" litros<br><img src='consumo.jpg'><th  width='20%'>Vazão instantânea: "+payload_parseado[2]+" l/h<br><img src='vazao.png'></th><th  width='20%'>Meta configurada: "+payload_parseado[3]+" litros<br><img src='meta.png'></th></th><th  width='20%'>Status do consumo: <br><img src='"+payload_parseado[4]+".png'></th></tr><tr><th  width='20%'>Versão firmware(medidor de luminosidade): "+payload_parseado[5]+"<br><img src='firmware.jpg'></th><th  width='20%'>Luminosidade: <br><img src='"+payload_parseado[6]+".jpg'></th></tr><tr><th  width='20%'>Versão firmware(medidor de temperatura): "+payload_parseado[7]+"<br><img src='firmware.jpg'></th><th  width='20%'>Temperatura: "+parseInt(payload_parseado[8], 10)+"ºC<br><img src='temperatura.jpg'></th></tr></table>";								
				$("#status_io").html(p); 
			};
		}
		Page.prototype.connect = function(){
			var url = "ws://test.mosquitto.org:8080/mqtt";
			mosq.connect(url);
		};
		Page.prototype.disconnect = function(){
			mosq.disconnect();
		};
		Page.prototype.subscribe = function(){
			var topic = $('#sub-topic-text')[0].value;
			mosq.subscribe(topic, 0);
		};
		Page.prototype.unsubscribe = function(){
			var topic = $('#sub-topic-text')[0].value;
			mosq.unsubscribe(topic);
		};
				
		Page.prototype.EnviaConfigsMeta = function(){
			var topic = "QCON2016SPEnvia";
			var emailaviso = $('#email-aviso')[0].value;
			var metaconsumo = $('#meta-comsumo')[0].value;
			var payload = "EnviaConfigsMetaAgua"+">"+metaconsumo+">"+emailaviso;
			var SomaBytesChavePublica = 1012;
		    var CodigoChar = 0;
			var CharCriptografado=" ";
			var i=0;
			var StringCriptografada = "";
			var TamanhoString = payload.length;
	
			for(i=0; i<TamanhoString; i++)
			{				
				CodigoChar = payload.charCodeAt(i);	
				CharCriptografado = ((CodigoChar+SomaBytesChavePublica) & 0xFF);
				StringCriptografada = StringCriptografada + String.fromCharCode(CharCriptografado);
			}
            
			mosq.publish(topic, btoa(StringCriptografada), 0);
		};
		
		Page.prototype.RequisitaInformacoes = function(){
			var topic = "QCON2016SPEnvia";
			var payload = "RequisitaInformacoesAgua";			
			var SomaBytesChavePublica = 1012;
		    var CodigoChar = 0;
			var CharCriptografado=" ";
			var i=0;
			var StringCriptografada = "";
			var TamanhoString = payload.length;
	
			for(i=0; i<TamanhoString; i++)
			{				
				CodigoChar = payload.charCodeAt(i);	
				CharCriptografado = ((CodigoChar+SomaBytesChavePublica) & 0xFF);
				StringCriptografada = StringCriptografada + String.fromCharCode(CharCriptografado);
			}
            
			mosq.publish(topic, btoa(StringCriptografada), 0);
		};
		
		Page.prototype.ResetConsumo = function(){
			var topic = "QCON2016SPEnvia";
			var payload = "ResetConsumoAgua";
			var SomaBytesChavePublica = 1012;
		    var CodigoChar = 0;
			var CharCriptografado=" ";
			var i=0;
			var StringCriptografada = "";
			var TamanhoString = payload.length;
	
			for(i=0; i<TamanhoString; i++)
			{				
				CodigoChar = payload.charCodeAt(i);	
				CharCriptografado = ((CodigoChar+SomaBytesChavePublica) & 0xFF);
				StringCriptografada = StringCriptografada + String.fromCharCode(CharCriptografado);
			}
            
			mosq.publish(topic, btoa(StringCriptografada), 0);
		};
		
		Page.prototype.IniciaCalibracao = function(){
			var topic = "QCON2016SPEnvia";
			var payload = "IniciaCalibracaoAgua";
			var SomaBytesChavePublica = 1012;
		    var CodigoChar = 0;
			var CharCriptografado=" ";
			var i=0;
			var StringCriptografada = "";
			var TamanhoString = payload.length;
	
			for(i=0; i<TamanhoString; i++)
			{				
				CodigoChar = payload.charCodeAt(i);	
				CharCriptografado = ((CodigoChar+SomaBytesChavePublica) & 0xFF);
				StringCriptografada = StringCriptografada + String.fromCharCode(CharCriptografado);
			}
            
			mosq.publish(topic, btoa(StringCriptografada), 0);
		
		};

		Page.prototype.FinalizaCalibracao = function(){
			var topic = "QCON2016SPEnvia";
			var payload = "FinalizaCalibracaoAgua";
			var SomaBytesChavePublica = 1012;
		    var CodigoChar = 0;
			var CharCriptografado=" ";
			var i=0;
			var StringCriptografada = "";
			var TamanhoString = payload.length;
	
			for(i=0; i<TamanhoString; i++)
			{				
				CodigoChar = payload.charCodeAt(i);	
				CharCriptografado = ((CodigoChar+SomaBytesChavePublica) & 0xFF);
				StringCriptografada = StringCriptografada + String.fromCharCode(CharCriptografado);
			}
            
			mosq.publish(topic, btoa(StringCriptografada), 0);
		};
		
		return Page;
	})();
	$(function(){
		return Main.controller = new Main.Page;
	});
}).call(this);

