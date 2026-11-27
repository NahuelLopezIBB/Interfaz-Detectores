/*
 * Contador de pulsos de 5 canales — firmware del ESP32 (DevKitC 38 pines).
 *
 * Cuenta flancos de subida en 5 entradas independientes usando el periférico
 * PCNT (una unidad por canal) y cada `tiempoActualizacion` ms envía por serie
 * las cuentas acumuladas en esa ventana.
 *
 * Pines de entrada (CH1..CH5): GPIO 32, 33, 27, 14, 25.
 *   Se evitaron los pines de arranque (strapping), los de la flash, los de
 *   UART0 (usados por el USB-serie) y los solo-entrada 34/35, que no tienen
 *   pull-up interno.
 *   Las señales reales (~2 V, ~1,5 µs) necesitan un comparador rápido a 3,3 V
 *   antes de llegar al ESP32 (pendiente).
 * GPIO 26: generador de prueba con tone(); se usa con un jumper 26 -> 32.
 *
 * Protocolo serie (115200 baudios), una línea por ventana:
 *
 *   t_ms,intervalo_ms,c0,c1,c2,c3,c4\n
 *
 *   t_ms         millis() del ESP32 al cierre de la ventana (tiempo relativo;
 *                vuelve a 0 si el ESP32 se reinicia).
 *   intervalo_ms duración de la ventana.
 *   c0..c4       cuentas de cada canal en esa ventana (diferencias, no
 *                acumulados).
 */
#include <Arduino.h>
#include "driver/pulse_cnt.h"

// Última lectura de cada contador; sirve para calcular la diferencia en la
// siguiente ventana. Es uint32_t para que la resta resuelva sola el desborde.
uint32_t cuentas_anterior[5];
// Duración de cada ventana de conteo, en ms.
unsigned long tiempoActualizacion = 250;
// Instante (millis) en que cerró la última ventana.
unsigned long t_anterior = 0;
// GPIO de entrada de cada canal (índice 0 = CH1).
const int puertos[5] = {32, 33, 27, 14, 25};

// Una unidad PCNT por canal: el conteo lo hace el hardware, sin usar la CPU
// ni interrupciones por pulso.
pcnt_unit_handle_t unidad[5] = {NULL};

/**
 * Inicializa el puerto serie, configura y arranca una unidad PCNT por canal,
 * enciende el generador de prueba y fija el inicio de la primera ventana.
 * Ante cualquier error del driver, ESP_ERROR_CHECK reinicia el ESP32.
 */
void setup()
{
  // put your setup code here, to run once:
  Serial.begin(115200);

  for (int i = 0; i < 5; i++)
  {
    // El contador de hardware es de 16 bits con signo. Con accum_count = 1 y
    // watch points en los límites (32767 y -1), el driver detecta cada vez
    // que se alcanza un límite, suma ese valor a un acumulador por software y
    // así extiende el conteo más allá de 16 bits.
    pcnt_unit_config_t cfg_unidad = {};
    cfg_unidad.low_limit = -1;
    cfg_unidad.high_limit = 32767;
    cfg_unidad.flags.accum_count = 1;
    ESP_ERROR_CHECK(pcnt_new_unit(&cfg_unidad, &unidad[i]));

    // Filtro anti-glitch: descarta pulsos de menos de 1000 ns (ruido), más
    // cortos que los pulsos reales de ~1,5 µs.
    pcnt_glitch_filter_config_t filtro = {};
    filtro.max_glitch_ns = 1000;
    ESP_ERROR_CHECK(pcnt_unit_set_glitch_filter(unidad[i], &filtro));

    pcnt_channel_handle_t canal = NULL;
    pcnt_chan_config_t cfg_canal = {};

    // Solo se usa la entrada de flancos; sin pin de nivel (-1) el conteo no
    // depende de ninguna señal de control.
    cfg_canal.edge_gpio_num = puertos[i];
    cfg_canal.level_gpio_num = -1;
    ESP_ERROR_CHECK(pcnt_new_channel(unidad[i], &cfg_canal, &canal));

    ESP_ERROR_CHECK(pcnt_channel_set_edge_action(canal,
                                                 PCNT_CHANNEL_EDGE_ACTION_INCREASE, // flanco de subida
                                                 PCNT_CHANNEL_EDGE_ACTION_HOLD));   // flanco de bajada.

    // Watch points en los límites: necesarios para que accum_count funcione.
    ESP_ERROR_CHECK(pcnt_unit_add_watch_point(unidad[i], 32767));
    ESP_ERROR_CHECK(pcnt_unit_add_watch_point(unidad[i], -1));

    ESP_ERROR_CHECK(pcnt_unit_enable(unidad[i]));
    ESP_ERROR_CHECK(pcnt_unit_clear_count(unidad[i]));
    ESP_ERROR_CHECK(pcnt_unit_start(unidad[i]));
  }
  // Generador de prueba: 100 Hz en GPIO26 (jumper 26 -> 32). Se mantiene a
  // propósito mientras no haya señales reales.
  tone(26, 100);
  // La primera ventana empieza recién acá, después de toda la
  // configuración, para que sea completa.
  t_anterior = millis();
}

/**
 * Cada vez que se cumple una ventana de `tiempoActualizacion` ms, lee los 5
 * contadores, calcula cuántos pulsos llegaron desde la ventana anterior y
 * envía la línea del protocolo serie. Actualiza `t_anterior` y
 * `cuentas_anterior`.
 */
void loop()
{

  // Se compara la diferencia (y no millis() >= t_anterior + intervalo) para
  // que el desborde de millis() (~49 días) no rompa la comparación.
  if (millis() - t_anterior >= tiempoActualizacion)
  {

    int valor[5] = {};
    uint32_t neto[5];
    // Se avanza el instante teórico de cierre (y no t_anterior = millis()):
    // así las ventanas no acumulan el retraso con que se atiende el loop.
    t_anterior += tiempoActualizacion;
    for (int i = 0; i < 5; i++)
    {
      ESP_ERROR_CHECK(pcnt_unit_get_count(unidad[i], &valor[i]));
    }
    // Se envían diferencias entre lecturas consecutivas. La resta se hace en
    // uint32_t: si el contador acumulado da la vuelta, la aritmética módulo
    // 2^32 sigue dando la diferencia correcta.
    uint32_t copia[5] = {};
    for (int i = 0; i < 5; i++)
    {
      copia[i] = valor[i];
      neto[i] = copia[i] - cuentas_anterior[i];

      cuentas_anterior[i] = copia[i];
    }
    // Línea del protocolo: t_ms,intervalo_ms,c0,c1,c2,c3,c4\n
    Serial.print(t_anterior);
    Serial.print(",");
    Serial.print(tiempoActualizacion);
    Serial.print(",");
    for (int i = 0; i < 5; i++)
    {
      if (i != 4)
      {
        Serial.print(neto[i]);
        Serial.print(",");
      }
      else
      {
        Serial.println(neto[i]);
      }
    }
  }
}
