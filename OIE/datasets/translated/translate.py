import pathlib
from OIE.datasets.conll2bioes import Conversor
import os
import spacy
from tqdm import tqdm
from OIE.datasets.main import criar_conll
import typer
from googletrans import Translator
from transformers import MarianMTModel, MarianTokenizer, pipeline
from transformers.pipelines.pt_utils import KeyDataset
from torch.utils.data import Dataset
import json

app = typer.Typer()


class LoadDataset:
    def __init__(self, dataset_path: str, dataset_name: str, out_path: str):
        self.dataset_name = dataset_name
        self.dataset_path = dataset_path

        with open(self.dataset_path +"/"+ self.dataset_name, "r", encoding="utf-8") as f:
            data = f.read()

        # selecionando apenas exts com arg0 rel e arg1
        data = data.split("\n\t")
        data_norm = []
        for ext in data:
            if "ARG5" not in ext:
                if "ARG4" not in ext:
                    if "ARG3" not in ext:
                        if "ARG2" not in ext:
                            if "ARG1" in ext:
                                if "V" in ext:
                                    if "ARG0" in ext:
                                        data_norm.append(ext)
        path = out_path+"/mod"
        pathlib.Path(path).mkdir(parents=True, exist_ok=True)
        lenght = len(data_norm)
        with open(path + "/" + dataset_name, "a", encoding="utf-8") as f:
            raw = data_norm[:10000]
            raw = "\n\t".join(raw)
            f.write(raw)
        Conversor(path+"/", dataset_name, out_path)

class ArgsRel:
    def __init__(self):
        try:
            self.nlp = spacy.load("pt_core_news_sm")
        except:
            os.system("python -m spacy download pt_core_news_lg")
            self.nlp = spacy.load("pt_core_news_sm")

    #Separa arg1, rel e arg2 da extração a partir da analise sintatica de dependencia da extração
    def get_args_rel(self, ext):
        doc = self.nlp(ext)
        arg1 = ""
        rel = ""
        arg2 = ""
        root_idx = (0,0)
        for token in doc:
            if (token.pos_ == "VERB" and token.dep_ == "ROOT"):
                rel += token.text + " "
                root_idx = (token.idx, token.idx + len(token.text))
        for token in doc:
            if token.idx < root_idx[0]:
                arg1 += token.text + " "
            if token.idx > root_idx[1]:
                arg2 += token.text + " "
        return arg1, rel, arg2

class Translators:
    def __init__(self):
        model_name = "Helsinki-NLP/opus-mt-tc-big-en-pt"
        self.pipe = pipeline("translation", model=model_name, device=0)
        self.google_translator = Translator()

    def google(self, sent):
        result = self.google_translator.translate(sent)
        return result

    def batch_google(self, dataset):
        sents_trad = self.google_translator.translate(dataset[0], src="en", dest="pt")
        exts_trad = self.google_translator.translate(dataset[1], src="en", dest="pt")
        return sents_trad, exts_trad

    def mt(self, text):
        trad_text = self.pipe(text, max_length=1000)[0]["translation_text"]
        return trad_text

    def batch_mt(self, dataset):

        trad = self.pipe(dataset[0])
        ext = self.pipe(dataset[1])
        return trad, ext


class TranslateDataset:
    def __init__(self, dataset_dir: str, dataset_name: str, out_path: str):
        self.dataset_dir = dataset_dir
        self.dataset_name = dataset_name
        self.out_path = out_path
        self.translators = Translators()

    def save_dict(self, data_dict):
        with open(self.out_path+"/saida_match/json_dump.json", "a", encoding="utf-8") as f:
            f.write(json.dumps(data_dict))


    def translate(self):
        # estrutura o dataset em um dicionario
        with open(f"{self.out_path}/conll2bioes_output/{self.dataset_name.replace('.conll', '.txt')}",
                  "r", encoding="utf-8") as f:
            data = f.read()
        data = data.split("\n\t")
        data = [ext.split("\n") for ext in data]
        #data = data[:2]
        for ext in data:
            for i in range(len(ext)):
                ext[i] = ext[i].split("\t")
        data_dict = {}
        counter = 0
        for ext in tqdm(data, desc="Traduzindo dataset"):
            sentence = ""
            arg0 = ""
            rel = ""
            arg1 = ""
            for e in ext:
                if e != [""]:
                    sentence += e[0] + " "
                    if "ARG0" in e[8]:
                        arg0 += e[0] + " "
                    if "ARG1" in e[8]:
                        arg1 += e[0] + " "
                    if "V" in e[8]:
                        rel += e[0] + " "

            # traduz sentença, arg0, rel e arg1
            sentence_trad = self.translators.mt(sentence)
            ext_trad = self.translators.mt(arg0 + rel + arg1)
            arg0_trad, rel_trad, arg1_trad = ArgsRel().get_args_rel(ext_trad)
            data_dict[str(counter)] = {"ID": counter, "sent": sentence_trad,
                                       "ext": [{"arg1": arg0_trad, "rel": rel_trad, "arg2": arg1_trad}]}
            counter += 1
        self.save_dict(data_dict)


    def translate2(self, batch_size):
        # estrutura o dataset em um dicionario
        with open(f"{self.out_path}/conll2bioes_output/{self.dataset_name.replace('.conll', '.txt')}",
                  "r", encoding="utf-8") as f:
            data = f.read()
        data = data.split("\n\t")
        data = [ext.split("\n") for ext in data]
        for ext in data:
            for i in range(len(ext)):
                ext[i] = ext[i].split("\t")

        data_dict = {}
        dataset = []
        sents = []
        exts = []
        for ext in tqdm(data, desc="Carregando dataset"):
            sentence = ""
            arg0 = ""
            rel = ""
            arg1 = ""
            for e in ext:
                if e != [""]:
                    sentence += e[0] + " "
                    if "ARG0" in e[8]:
                        arg0 += e[0] + " "
                    if "ARG1" in e[8]:
                        arg1 += e[0] + " "
                    if "V" in e[8]:
                        rel += e[0] + " "
            sents.append(sentence)
            exts.append(arg0+rel+arg1)
        dataset.append(sents)
        dataset.append(exts)

        #batching
        dataloader = []
        for i in tqdm(range(0, len(dataset[0]), batch_size), desc="dataloader"):
            batch = [dataset[0][i:i+batch_size], dataset[1][i:i+batch_size]]
            dataloader.append(batch)

        #traduz dataset
        all_sent = []
        all_ext = []
        for batch in tqdm(dataloader, desc=f"Traduzindo dataset com batching de {batch_size}"):
            sent, ext = self.translators.batch_mt(batch)
            all_sent += sent
            all_ext += ext

        #identifica elementos da tripla traduzida e armazena em um dicionario
        counter = 0
        for sample in tqdm(zip(all_sent, all_ext), desc="Armazenando tradução", total=len(all_sent)):
            arg0_trad, rel_trad, arg1_trad = ArgsRel().get_args_rel(sample[1]["translation_text"])
            data_dict[str(counter)] = {"ID": counter, "sent": sample[0]["translation_text"],
                                       "ext": [{"arg1": arg0_trad, "rel": rel_trad, "arg2": arg1_trad}]}
            counter += 1

        #salva dicionario
        self.save_dict(data_dict)

@app.command()
def run(batch_size:int ,dataset_dir: str, dataset_name: str, test_size: float, dev_size: float):
    converted = True
    OUT_NAME = dataset_name.replace(".conll", "")
    INPUT_PATH = ""

    path = "outputs"+"/"+OUT_NAME
    pathlib.Path(path).mkdir(parents=True, exist_ok=True)
    json_dir = path+"/saida_match"
    pathlib.Path(json_dir).mkdir(parents=True, exist_ok=True)

    LoadDataset(dataset_dir, dataset_name, path)
    TranslateDataset(dataset_dir, dataset_name, path).translate2(batch_size)
    criar_conll(OUT_NAME, INPUT_PATH, test_size, dev_size, converted)

if __name__ == "__main__":
    app()