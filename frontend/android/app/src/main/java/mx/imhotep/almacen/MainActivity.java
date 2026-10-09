package mx.imhotep.almacen;

import com.getcapacitor.BridgeActivity;
import android.os.Bundle;
import android.webkit.WebSettings;
import android.widget.LinearLayout;
import android.widget.TextView;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

public class MainActivity extends BridgeActivity {
    @Override
    public void onCreate(Bundle savedInstanceState) {
        registerPlugin(HttpSeguroPlugin.class);
        registerPlugin(ImpresionPlugin.class);
        super.onCreate(savedInstanceState);
        // Antes de pintar React: un WebView viejo no puede dibujar Tailwind 4.
        String agente = WebSettings.getDefaultUserAgent(this);
        Matcher motor = Pattern.compile("Chrome/(\\d+)").matcher(agente);
        if (!motor.find() || Integer.parseInt(motor.group(1)) < 111) {
            LinearLayout aviso = new LinearLayout(this);
            aviso.setOrientation(LinearLayout.VERTICAL);
            aviso.setGravity(android.view.Gravity.CENTER);
            int margen = (int) (24 * getResources().getDisplayMetrics().density);
            aviso.setPadding(margen, margen, margen, margen);
            TextView texto = new TextView(this);
            texto.setText(R.string.webview_desactualizado);
            texto.setTextSize(18);
            aviso.addView(texto);
            setContentView(aviso);
        }
    }
}
