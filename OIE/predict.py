from flair.models import SequenceTagger
from flair.data import Sentence
import typer

app = typer.Typer()

class Predictor:
    def __init__(self, model:str):
        try:
            self.oie = SequenceTagger.load("train_output/" + model + "/best-model.pt")
        except:
            self.oie = SequenceTagger.load("train_output/" + model + "/final-model.pt")

    def display(self, maior, exts, sentenca, tripla, sentence: Sentence):
        print("\n" * 1)
        print("| ", "-" * len(maior), " |")
        for ext in exts:
            print("Extração: ", ext[0][0] + " " + ext[1][0] + " " + ext[2][0])
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
        sentence = Sentence(text)
        self.oie.predict(sentence)

        # separa elementos da tripla
        arg0 = [(span.text, span.score, span.tag,[span.start_position, span.end_position]) for span in sentence.get_spans('label') if span.tag == "ARG0"]
        rel = [(span.text, span.score, span.tag,[span.start_position, span.end_position]) for span in sentence.get_spans('label') if span.tag == "V"]
        arg1 = [(span.text, span.score, span.tag,[span.start_position, span.end_position]) for span in sentence.get_spans('label') if span.tag == "ARG1"]


        elems = arg0
        for r in rel:
            insert = False
            for i, e in enumerate(elems):
                if r[3][0] < e[3][0] and not insert:
                    elems.insert(elems.index(e), r)
                    insert = True
            if not insert:
                elems.append(r)

        for a in arg1:
            insert = False
            for i, e in enumerate(elems):
                if a[3][0] < e[3][0] and not insert:
                    elems.insert(elems.index(e), a)
                    insert = True
            if not insert:
                elems.append(a)

        # monta triplas
        exts = []
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
                        last_rel = el
                    else:
                        if ext[-1][2] == "V":
                            ext.append(el)
                            last_rel = el

                        if ext[-1][2] == "ARG1":
                            if last_arg0[3][1] < el[3][0]:
                                exts.append(ext)
                                ext = [last_arg0, el]
                                last_rel = el
                            else:
                                ext.append(el)
                                last_rel = el

            elif el[2] == "ARG1":
                if len(ext) > 0:
                    if ext[-1][2] == "V":
                        ext.append(el)
                        last_arg1 = el
                    else:
                        if ext[-1][2] == "ARG1":
                            ext.append(el)
                            last_arg1 = el

        n = ""
        for e in ext:
            n += e[2] + " "
        if "ARG0" in n and "V" in n and "ARG1" in n:
            exts.append(ext)
        return exts


@app.command()
def run(model:str, text:str, show_output: bool = True):
    predictor = Predictor(model)
    predictor.pred(text, show_output)

if __name__ == "__main__":
    app()