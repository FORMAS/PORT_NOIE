from flair.models import SequenceTagger
from flair.data import Sentence
import typer
from OIE.datasets.validated_splits.contractions import transform_portuguese_contractions, clean_extraction

app = typer.Typer()

class Predictor:
    def __init__(self, model:str):
        try:
            self.oie = SequenceTagger.load("train_output/" + model + "/best-model.pt")
            print("best model loaded")
        except:
            self.oie = SequenceTagger.load("train_output/" + model + "/final-model.pt")
            print("final model loaded")

    def display(self, maior, exts, sentenca, tripla, sentence: Sentence):
        print("\n" * 1)
        print(maior)
        print("| ", "-" * len(maior), " |")
        extraction = "extração: "
        for ext in exts:
            for e in ext:
                extraction += e[0] + " "
            print("| ", extraction, " " * (len(maior) - (len(extraction) + 1)), " |")
            extraction = "extração: "
        print("| ", "-" * len(maior), " |")
        print("\n" * 1)
        print("| ", "-" * len(maior), " |")
        print("| ", int((len(maior) - len("MAIS INFO")) / 2 - 1) * "-", "MAIS INFO",
              int((len(maior) - len("MAIS INFO")) / 2) * "-", " |")
        print("| ", "-" * len(maior), " |")
        print("| ", "sentença: ", " " * (len(maior) - (len("sentença: ") + 1)), " |")
        print("| ", sentenca, " " * (len(maior) - (len(sentenca) + 1)), " |")
        print("| ", "-" * len(maior), " |")
        print("| ", "extrações: ", " " * (len(maior) - (len("extrações: ") + 1)), " |")
        print("| ", tripla, " " * (len(maior) - (len(tripla) + 1)), " |")
        print("| ", "-" * len(maior), " |")
        print("| ", "probs: ", " " * (len(maior) - (len("probs: ") + 1)), " |")
        print("| ", sentence.get_spans('label'), " " * (len(maior) - (len(str(sentence.get_spans('label'))) + 1)), " |")
        print("| ", "-" * len(maior), " |")


    def pred(self, text:str, show_output: bool):
        exts = []
        sentences = [text]
        #if text[-1] == ".":
            #sentences.append(text[:-1])

        #if len(text)>200 and text.count(".")>1:
            #split = [t for t in text.split(".")]
            #if len(split) > 1:
                #for s in split:
                    #if s != "":
                        #sentences.append(s)

        #split = [t for t in text.split(",")]
        #if len(split) > 1:
            #for s in split:
                #if s != "":
                    #sentences.append(s)


        for sentenca in sentences:
            sentence = Sentence(sentenca)
            self.oie.predict(sentence)

            # separa elementos da tripla
            arg0 = [(span.text, span.score, span.tag,[span.start_position, span.end_position]) for span in sentence.get_spans('label') if span.tag == "ARG0"]
            rel = [(span.text, span.score, span.tag,[span.start_position, span.end_position]) for span in sentence.get_spans('label') if span.tag == "V"]
            arg1 = [(span.text, span.score, span.tag,[span.start_position, span.end_position]) for span in sentence.get_spans('label') if span.tag == "ARG1"]

            elems = arg0
            for r in rel:
                insert = False
                for i, e in enumerate(elems):
                    if r[3][1] <= e[3][0] and not insert:
                        elems.insert(elems.index(e), r)
                        insert = True
                if not insert:
                    elems.append(r)

            for a in arg1:
                insert = False
                for i, e in enumerate(elems):
                    if a[3][1] <= e[3][0] and not insert:
                        elems.insert(elems.index(e), a)
                        insert = True
                if not insert:
                    elems.append(a)

            # monta triplas
            ext = []
            last_arg0 = ()
            last_rel = ()
            last_arg1 = ()
            for i, el in enumerate(elems):
                if el[2] == "ARG0":
                    if len(ext) == 0:
                        ext.append(el)
                        last_arg0 = el
                    else:
                        if ext[-1][2] == "ARG0":
                            ext.append(el)
                            last_arg0 = el

                elif el[2] == "V":
                    if len(ext) > 0:
                        if ext[-1][2] == "ARG0":
                            ext.append(el)
                            #last_rel = el
                        else:
                            if ext[-1][2] == "V":
                                ext.append(el)
                                #last_rel = el

                            if ext[-1][2] == "ARG1":
                                if last_arg0[3][1] < el[3][0]:
                                    exts.append(ext)
                                    ext = [last_arg0, el]
                                    #last_rel = el
                                else:
                                    ext.append(el)
                                    #last_rel = el

                elif el[2] == "ARG1":
                    if len(ext) > 0:
                        if ext[-1][2] == "V":
                            ext.append(el)
                            #last_arg1 = el
                        else:
                            if ext[-1][2] == "ARG1":
                                ext.append(el)
                                #last_arg1 = el
            n = ""
            for e in ext:
                n += e[2] + " "
            if "ARG0" in n and "V" in n and "ARG1" in n:
                exts.append(ext)

            if show_output:
                if len(sentence.get_spans('label')) >= 3:
                    maior = ""
                    if len(maior) < len(sentence):
                        maior = sentence
                    if len(maior) < len(str(sentence.get_spans('label'))):
                        maior = str(sentence.get_spans('label'))
                    if len(maior) < len(text):
                        maior = text
                    self.display(maior, exts, text, str(sentence).split("]: ")[1], sentence)

        # filtra extrações iguais
        if len(exts) > 1:
            repeated_idxs = []
            i = 0
            while i < len(exts):
                current = exts[i]
                ext_str = " ".join([e[0] for e in current])
                j = i+1
                while j < len(exts):
                    next = exts[j]
                    next_str = " ".join([e[0] for e in next])
                    if ext_str == next_str:
                        repeated_idxs.append(j)
                    j += 1
                i += 1
            repeated_idxs = list(set(repeated_idxs))
            for i in range(len(repeated_idxs)):
                exts.pop(repeated_idxs[i]-i)

        #print(exts)
        return exts


@app.command()
def run(model:str, text:str, show_output: bool = False):
    predictor = Predictor(model)
    text = transform_portuguese_contractions(text)
    predictor.pred(text, show_output)

if __name__ == "__main__":
    app()