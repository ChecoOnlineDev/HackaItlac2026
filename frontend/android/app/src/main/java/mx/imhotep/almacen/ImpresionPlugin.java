package mx.imhotep.almacen;

import android.content.Context;
import android.print.PrintAttributes;
import android.print.PrintManager;
import com.getcapacitor.Plugin;
import com.getcapacitor.PluginCall;
import com.getcapacitor.PluginMethod;
import com.getcapacitor.annotation.CapacitorPlugin;

/** Impresión normal y Guardar como PDF de Android para el documento de la pantalla. */
@CapacitorPlugin(name = "Impresion")
public class ImpresionPlugin extends Plugin {
    @PluginMethod
    public void imprimir(PluginCall call) {
        getActivity().runOnUiThread(() -> {
            try {
                PrintManager impresora = (PrintManager) getActivity().getSystemService(Context.PRINT_SERVICE);
                if (impresora == null) {
                    call.reject("Este equipo no tiene servicio de impresión.");
                    return;
                }
                impresora.print("IMHOTEP", getBridge().getWebView().createPrintDocumentAdapter("IMHOTEP"),
                        new PrintAttributes.Builder().build());
                call.resolve();
            } catch (Exception e) {
                call.reject("No pudimos abrir la impresión de este documento.");
            }
        });
    }
}
