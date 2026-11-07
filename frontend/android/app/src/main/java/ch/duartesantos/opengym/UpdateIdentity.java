package ch.duartesantos.opengym;

import java.util.Arrays;

/** Update identity checks independent of Android framework calls, usable in JVM tests. */
final class UpdateIdentity {
    static boolean valid(String installed, long installedVersion, byte[][] installedSigners,
                         String candidate, long candidateVersion, byte[][] candidateSigners) {
        if (installed == null || !installed.equals(candidate) || candidateVersion <= installedVersion) return false;
        if (installedSigners == null || candidateSigners == null || installedSigners.length == 0
                || installedSigners.length != candidateSigners.length) return false;
        for (byte[] signer : installedSigners) {
            boolean found = false;
            for (byte[] other : candidateSigners) if (signer != null && other != null && Arrays.equals(signer, other)) found = true;
            if (!found) return false;
        }
        return true;
    }
}
