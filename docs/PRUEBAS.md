# Pruebas

```bash
pip install -r requirements-dev.txt
pytest            # 42 pruebas, BD temporal por prueba, CSRF desactivado salvo en su propia prueba
```

Cada prueba crea una base nueva y la llena con `flask seed`, de modo que también valida el sembrado.

## `tests/test_modelos.py` — reglas de negocio
| Área | Casos |
|---|---|
| Acceso | login correcto/incorrecto; bloqueo tras 5 intentos aun con clave correcta; registro duplicado y contraseña débil; recuperación sin revelar existencia |
| Membresías | beneficiarios solo en familiar y límite; estados suspendida/vencida e historial |
| Invitados | límite mensual; fecha pasada; listado de esperados |
| Reservas | sin traslape en exclusivas (contiguas sí); horario, aforo y bloqueo; piscina compartida suma aforo; modificar/cancelar/confirmar; no cancelar finalizadas; sin membresía activa no reserva |
| Cuentas | morosos y pago manual (no doble pago); generación idempotente; PDF válido |

## `tests/test_web.py` — recorridos HTTP
Páginas públicas; redirección de rutas protegidas; recorrido del socio; PDF por HTTP; aislamiento socio/admin; reserva ajena = 404; **matriz de permisos por rol**; humo de todas las rutas GET de admin y socio; **CSRF obligatorio**; cabeceras CSP; HTML accesible básico; reserva y traslape por formulario; pago de cargo.

### Pantallas del prototipo
`test_modales_del_prototipo_presentes` (M01–M04), `test_montos_en_colones`, `test_editar_y_quitar_beneficiario`, `test_socio_cambia_tipo_de_membresia`, `test_registrar_pago_con_fecha`, `test_plantilla_vista_previa_no_guarda`, `test_calendario_semanal_con_detalle`, `test_ocupacion_y_reportes`, `test_bloqueo_desde_modal`.

## Verificaciones manuales recomendadas (no automatizadas)
- Accesibilidad: navegar solo con teclado, lector de pantalla y Lighthouse/axe en las páginas principales.
- Rendimiento: Lighthouse en móvil.
- Concurrencia: dos reservas simultáneas en la misma franja (ver limitación en [ARQUITECTURA.md](ARQUITECTURA.md)).
- Envío real de correo con SMTP configurado.
