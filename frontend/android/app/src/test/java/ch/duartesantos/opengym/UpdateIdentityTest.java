package ch.duartesantos.opengym;

import org.junit.Test;
import static org.junit.Assert.*;

public class UpdateIdentityTest {
    private final byte[][] signer = {{1, 2, 3}};

    @Test public void onlyNewerSameApplicationAndSignerCanUpdate() {
        assertTrue(UpdateIdentity.valid("io.github.coney97.opengym.zh", 1, signer, "io.github.coney97.opengym.zh", 2, signer));
        assertFalse(UpdateIdentity.valid("io.github.coney97.opengym.zh", 1, signer, "ch.duartesantos.opengym", 2, signer));
        assertFalse(UpdateIdentity.valid("io.github.coney97.opengym.zh", 1, signer, "io.github.coney97.opengym.zh", 2, new byte[][]{{9}}));
        assertFalse(UpdateIdentity.valid("io.github.coney97.opengym.zh", 1, signer, "io.github.coney97.opengym.zh", 1, signer));
        assertFalse(UpdateIdentity.valid("io.github.coney97.opengym.zh", 2, signer, "io.github.coney97.opengym.zh", 1, signer));
        assertFalse(UpdateIdentity.valid("io.github.coney97.opengym.zh", 1, null, "io.github.coney97.opengym.zh", 2, signer));
    }
}
