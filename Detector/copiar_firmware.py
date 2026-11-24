Import("env")
import os, shutil

def copiar(source, target, env):
    destino = os.path.join(env.subst("$PROJECT_DIR"), "firmware")
    os.makedirs(destino, exist_ok=True)
    for ext in ("bin", "elf"):
        shutil.copy(env.subst("$BUILD_DIR/${PROGNAME}." + ext), destino)
    print("Firmware copiado a", destino)

env.AddPostAction("$BUILD_DIR/${PROGNAME}.bin", copiar)