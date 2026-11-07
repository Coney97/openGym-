package ch.duartesantos.opengym;

import org.junit.Test;
import static org.junit.Assert.*;

public class NativeWordsTest {
    @Test public void translatesFallbacksWithoutTouchingStoredIdentifiers() {
        assertEquals("暂停", NativeWords.chinese("Pause"));
        assertEquals("休息结束，开始下一组！", NativeWords.chinese("Rest’s over. Next set!"));
        assertEquals("− 15秒", NativeWords.chinese("− 15s"));
        assertEquals("streak", NativeWords.chinese("streak"));
        assertNull(NativeWords.chinese(null));
    }
}
