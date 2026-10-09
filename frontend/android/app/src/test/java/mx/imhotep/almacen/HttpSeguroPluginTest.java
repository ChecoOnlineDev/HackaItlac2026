package mx.imhotep.almacen;

import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;
import org.junit.Test;

public class HttpSeguroPluginTest {
    @Test
    public void AC_24_reconoce_encabezados_de_cookie_sin_importar_mayusculas() {
        assertTrue(HttpSeguroPlugin.esCookie("Set-Cookie"));
        assertTrue(HttpSeguroPlugin.esCookie("set-cookie"));
        assertTrue(HttpSeguroPlugin.esCookie("SET-COOKIE2"));
        assertFalse(HttpSeguroPlugin.esCookie("Content-Disposition"));
        assertFalse(HttpSeguroPlugin.esCookie("Content-Type"));
    }
}
