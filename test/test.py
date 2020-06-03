import subprocess
import re
from subprocess import check_output
if __name__ == "__main__":
    full_command = "python test\\run_game.py -m AcropolisLE -p ReaperRushBot -o WorkerRushBot"
    out = str(check_output(full_command.split(" ")))
    # out2 = check_output(full_command.split(" "))
    start = r"Result for player 1 - Bot ReaperRushBot(Terran): "
    end = r"\r"
    out = (out.split(start))[1].split(end)[0]
    print(out)
