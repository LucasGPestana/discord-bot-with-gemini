import discord

import google.generativeai as genai
from google.ai.generativelanguage_v1beta.types.content import Content
from google.ai.generativelanguage_v1beta.types.content import Part # Representa a parte de um conteúdo (Content), que encapsula os textos (text) do chat (Prompts e respostas)

import json
import datetime
import os
import re

from dotenv import load_dotenv

load_dotenv()

genai.configure(api_key=os.getenv("API_KEY"))

class ClientConn(discord.Client):

  __file_regex = re.compile(r"(?<=\s)[\w\s\d\\/\-\.\_\:]+(.json)$") # Padrão regex que identifica o diretório de um arquivo ".json"

  def __init__(self, *, intents, **options):

    super().__init__(intents=intents, **options)

    self.__model = genai.GenerativeModel(model_name="models/gemini-1.0-pro-latest")
    
    self.__session = self.__model.start_chat(history=[])

    self.__commands = {"load-history": self.load_history,
                       "save-history": self.save_history,
                       "prompt": self.prompt}
  
  # Envia uma mensagem (prompt) para o modelo da sessão de chat
  async def prompt(self, message, _):

    response = self.__session.send_message(message.content[len("!prompt"):])

    page_step = 2000

    # Paginação para dividir o texto de 2000 a 2000 caracteres, correspondente ao limite de uma mensagem no Discord
    for i in range(0, len(response.text), page_step + 1):

      if i + 1 >= len(response.text):

        await message.channel.send(content=response.text[i:])
        
      else:

        await message.channel.send(content=response.text[i:page_step])
  
  # Carrega o histórico de conversas de uma sessão de chat
  async def load_history(self, message, filename):

    if not os.path.isfile(filename) or not filename.endswith(".json"):

      await message.channel.send("O caminho especificado não se refere a um arquivo JSON, ou não existe!")
      return
    
    with open(filename, 'r') as file_stream:

      content_objs = json.loads(file_stream.read())
    
    content_objs = [Content(role=content_args["role"],
                            parts=[Part(text=content_args["text"])]) for content_args in content_objs]
    
    self.__session = self.__model.start_chat(history=content_objs)

    await message.channel.send(f"Uma nova sessão de chat foi criada com as mensagens carregadas de {filename}!")

  # Salva o histórico de conversa de uma sessão de chat
  async def save_history(self, message, filename=None):

    # Caso o caminho do arquivo não seja passado, um arquivo com o nome da data e horário do cliente será criado
    if filename is None:

      filename = datetime.datetime.now().strftime("%d-%m-%Y %H-%M-%S") + ".json"

    if not filename.endswith(".json"):

      await message.channel.send("Você precisa especificar um caminho de arquivo JSON.")
      return
    
    content_objs = [{"text": content.parts[0].text, 
                     "role": content.role} for content in self.__session.history]

    with open(filename, 'w') as file_stream:
      
      file_stream.write(json.dumps(content_objs))
    
    await message.channel.send(f"O arquivo {filename}, referente a nossa conversa, foi salvada com sucesso!")

  async def on_ready(self):

    print(f"Logado como {self.user.name}")
  
  async def on_message(self, message):

    content = message.content

    if content.startswith("!"):

      filename = None
      filename_match = ClientConn.__file_regex.search(content)

      if filename_match: 
        
        filename = filename_match.group().strip()
      
      if not self.__commands.get(content[1:content.find(" ")]):

        await message.channel.send("Não compreendo esse comando!")
        return
      
      await self.__commands[content[1:content.index(" ")]](message, filename)

if __name__ == "__main__":

  intents = discord.Intents.default()
  intents.message_content = True

  client_conn = ClientConn(intents=intents)

  client_conn.run(os.getenv("BOT_TOKEN"))


