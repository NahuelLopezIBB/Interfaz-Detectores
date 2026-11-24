#include <Arduino.h>
#include "driver/pulse_cnt.h"

uint32_t cuentas_anterior[5];
unsigned long tiempoActualizacion = 250;
unsigned long t_anterior = 0;
const int puertos[5] = {32, 33, 27, 14, 25};

pcnt_unit_handle_t unidad[5] = {NULL};

void setup()
{
  // put your setup code here, to run once:
  Serial.begin(115200);

  for (int i = 0; i < 5; i++)
  {
    pcnt_unit_config_t cfg_unidad = {};
    cfg_unidad.low_limit = -1;
    cfg_unidad.high_limit = 32767;
    cfg_unidad.flags.accum_count = 1;
    ESP_ERROR_CHECK(pcnt_new_unit(&cfg_unidad, &unidad[i]));

    pcnt_glitch_filter_config_t filtro = {};
    filtro.max_glitch_ns = 1000;
    ESP_ERROR_CHECK(pcnt_unit_set_glitch_filter(unidad[i], &filtro));

    pcnt_channel_handle_t canal = NULL;
    pcnt_chan_config_t cfg_canal = {};

    cfg_canal.edge_gpio_num = puertos[i];
    cfg_canal.level_gpio_num = -1;
    ESP_ERROR_CHECK(pcnt_new_channel(unidad[i], &cfg_canal, &canal));

    ESP_ERROR_CHECK(pcnt_channel_set_edge_action(canal,
                                                 PCNT_CHANNEL_EDGE_ACTION_INCREASE, // flanco de subida
                                                 PCNT_CHANNEL_EDGE_ACTION_HOLD));   // flanco de bajada.

    ESP_ERROR_CHECK(pcnt_unit_add_watch_point(unidad[i], 32767));
    ESP_ERROR_CHECK(pcnt_unit_add_watch_point(unidad[i], -1));

    ESP_ERROR_CHECK(pcnt_unit_enable(unidad[i]));
    ESP_ERROR_CHECK(pcnt_unit_clear_count(unidad[i]));
    ESP_ERROR_CHECK(pcnt_unit_start(unidad[i]));
  }
  tone(26, 50000);
  t_anterior = millis();
}

void loop()
{

  if (millis() - t_anterior >= tiempoActualizacion)
  {

    t_anterior += tiempoActualizacion;
    int valor[5] = {};
    uint32_t neto[5];

    for (int i = 0; i < 5; i++)
    {
      ESP_ERROR_CHECK(pcnt_unit_get_count(unidad[i], &valor[i]));
    }
    uint32_t copia[5] = {};
    for (int i = 0; i < 5; i++)
    {
      copia[i] = valor[i];
      neto[i] = copia[i] - cuentas_anterior[i];

      cuentas_anterior[i] = copia[i];
    }
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
