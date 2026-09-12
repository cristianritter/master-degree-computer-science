import com.github.javaparser.JavaParser;
import com.github.javaparser.ast.CompilationUnit;
import com.github.javaparser.ast.Node;
import com.github.javaparser.ast.NodeList;
import com.github.javaparser.ast.body.ClassOrInterfaceDeclaration;
import com.github.javaparser.ast.body.MethodDeclaration;

import java.io.InputStream;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import java.util.Set;
import java.util.regex.Pattern;
import java.util.stream.Stream;

/**
 * Replica a decisao do JNose (JNoseCore.isTestFile + flowClass) para achar os
 * arquivos que ele aceita como teste mas cujo TestClass.name fica nulo - os que
 * derrubam a analise do projeto inteiro com NullPointerException.
 */
public class AchaNulos {

    static final Set<String> IGNORAR =
            Set.of("target", "build", "classes", ".git", "node_modules", "out", "bin", "dist");

    static final List<Pattern> NOMES = List.of(
            Pattern.compile("^.*test\\d*$"), Pattern.compile("^.*testcase\\d*$"),
            Pattern.compile("^.*tests\\d*$"), Pattern.compile("^test.*"),
            Pattern.compile("^testcase.*"), Pattern.compile("^tests.*"));

    /** Mesma travessia do flowClass: so ClassOrInterfaceDeclaration define o nome. */
    static boolean achaClasse(NodeList<?> nodes) {
        for (Node node : nodes) {
            if (node instanceof ClassOrInterfaceDeclaration c) {
                return true;
            }
            if (node instanceof MethodDeclaration m && achaClasse(m.getAnnotations())) {
                return true;
            }
        }
        return false;
    }

    static boolean nomeFicaNulo(Path arquivo) {
        try (InputStream in = Files.newInputStream(arquivo)) {
            CompilationUnit cu = JavaParser.parse(in);
            for (Object lista : cu.getNodeLists()) {
                if (achaClasse((NodeList<?>) lista)) {
                    return false;
                }
            }
            // sem classe: so quebra se o JNose ainda assim aceitar como teste,
            // e ele aceita com base apenas nos imports de JUnit
            for (var imp : cu.getImports()) {
                String nome = imp.getNameAsString();
                if (nome.contains("org.junit") || nome.contains("junit.framework")) {
                    return true;
                }
            }
            return false;
        } catch (Exception e) {
            return false;  // nao parseia: o JNose captura e ignora o arquivo
        }
    }

    public static void main(String[] args) throws Exception {
        Path raiz = Path.of(args[0]);
        try (Stream<Path> caminhos = Files.walk(raiz)) {
            caminhos.filter(Files::isRegularFile)
                    .filter(p -> p.toString().toLowerCase().endsWith(".java"))
                    .filter(p -> {
                        for (Path parte : raiz.relativize(p)) {
                            if (IGNORAR.contains(parte.toString())) return false;
                        }
                        return true;
                    })
                    .filter(p -> {
                        String base = p.getFileName().toString();
                        base = base.substring(0, base.lastIndexOf('.')).toLowerCase();
                        for (Pattern pat : NOMES) if (pat.matcher(base).matches()) return true;
                        return false;
                    })
                    .filter(AchaNulos::nomeFicaNulo)
                    .forEach(p -> System.out.println(raiz.relativize(p)));
        }
    }
}
