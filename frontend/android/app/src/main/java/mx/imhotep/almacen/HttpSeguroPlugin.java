package mx.imhotep.almacen;

import com.getcapacitor.JSObject;
import com.getcapacitor.PluginCall;
import com.getcapacitor.PluginMethod;
import com.getcapacitor.annotation.CapacitorPlugin;
import com.getcapacitor.plugin.CapacitorHttp;
import java.util.ArrayList;
import java.util.Iterator;
import java.util.List;

/** AC-24: las cookies se procesan nativamente pero nunca regresan al puente JS. */
@CapacitorPlugin(name = "CapacitorHttp")
public class HttpSeguroPlugin extends CapacitorHttp {
    static boolean esCookie(String nombre) {
        return "Set-Cookie".equalsIgnoreCase(nombre) || "Set-Cookie2".equalsIgnoreCase(nombre);
    }

    private PluginCall sinCookies(PluginCall original) {
        return new PluginCall(null, original.getPluginId(), original.getCallbackId(),
                original.getMethodName(), original.getData()) {
            @Override
            public void resolve(JSObject datos) {
                JSObject encabezados = datos.getJSObject("headers");
                if (encabezados != null) {
                    List<String> quitar = new ArrayList<>();
                    Iterator<String> claves = encabezados.keys();
                    while (claves.hasNext()) {
                        String nombre = claves.next();
                        if (esCookie(nombre)) quitar.add(nombre);
                    }
                    for (String nombre : quitar) encabezados.remove(nombre);
                    datos.put("headers", encabezados);
                }
                original.resolve(datos);
            }

            @Override
            public void resolve() { original.resolve(); }

            @Override
            public void reject(String mensaje, String codigo, Exception causa, JSObject datos) {
                // Las excepciones de transporte no deben registrar datos de petición o cookies.
                original.reject("No pudimos conectar con el servidor.", codigo);
            }
        };
    }

    @Override @PluginMethod
    public void request(PluginCall call) { super.request(sinCookies(call)); }
    @Override @PluginMethod
    public void get(PluginCall call) { super.get(sinCookies(call)); }
    @Override @PluginMethod
    public void post(PluginCall call) { super.post(sinCookies(call)); }
    @Override @PluginMethod
    public void put(PluginCall call) { super.put(sinCookies(call)); }
    @Override @PluginMethod
    public void patch(PluginCall call) { super.patch(sinCookies(call)); }
    @Override @PluginMethod
    public void delete(PluginCall call) { super.delete(sinCookies(call)); }
}
