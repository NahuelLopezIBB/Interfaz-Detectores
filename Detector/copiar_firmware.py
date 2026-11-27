"""Script extra de PlatformIO: copia el firmware compilado a `firmware/`.

El `build_dir` está fuera del proyecto (la ruta del proyecto tiene caracteres
no ASCII que rompen el linker), pero Wokwi busca `firmware.bin`/`.elf` en una
ruta fija dentro del proyecto (ver `wokwi.toml`). Este script los copia ahí
después de cada compilación.
"""
# `Import` lo inyecta SCons (PlatformIO) al ejecutar el script; no es Python
# estándar. Trae el entorno de compilación `env`.
Import("env")
import os, shutil

def copiar(source, target, env):
    """Copia `${PROGNAME}.bin` y `.elf` desde `$BUILD_DIR` a `<proyecto>/firmware`.

    Firma de acción post-compilación de SCons: `source` y `target` no se usan;
    `env` se usa para expandir las variables de ruta. Crea la carpeta destino
    si no existe y sobrescribe los archivos anteriores.
    """
    destino = os.path.join(env.subst("$PROJECT_DIR"), "firmware")
    os.makedirs(destino, exist_ok=True)
    for ext in ("bin", "elf"):
        shutil.copy(env.subst("$BUILD_DIR/${PROGNAME}." + ext), destino)
    print("Firmware copiado a", destino)

# Se engancha a la generación del .bin, que es el último artefacto del
# build; para entonces el .elf ya existe.
env.AddPostAction("$BUILD_DIR/${PROGNAME}.bin", copiar)