package ch.duartesantos.opengym;

import android.app.Application;
import android.app.LocaleManager;
import android.content.Context;
import android.content.res.Configuration;
import android.os.Build;
import android.os.LocaleList;
import java.util.Locale;

/** The dedicated edition uses Chinese resources even when the device uses another language. */
public class ChineseApplication extends Application {
    static Context localized(Context base) {
        if (!BuildConfig.CHINESE_EDITION) return base;
        Configuration config = new Configuration(base.getResources().getConfiguration());
        config.setLocale(Locale.SIMPLIFIED_CHINESE);
        config.setLayoutDirection(Locale.SIMPLIFIED_CHINESE);
        return base.createConfigurationContext(config);
    }

    @Override protected void attachBaseContext(Context base) {
        super.attachBaseContext(localized(base));
    }

    @Override public void onCreate() {
        super.onCreate();
        if (BuildConfig.CHINESE_EDITION) {
            Locale.setDefault(Locale.SIMPLIFIED_CHINESE);
            if (Build.VERSION.SDK_INT >= 33) {
                LocaleManager manager = getSystemService(LocaleManager.class);
                if (manager != null && !"zh-CN".equals(manager.getApplicationLocales().toLanguageTags())) {
                    manager.setApplicationLocales(LocaleList.forLanguageTags("zh-CN"));
                }
            }
        }
    }
}
