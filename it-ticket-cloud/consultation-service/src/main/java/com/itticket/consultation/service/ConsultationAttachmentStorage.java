package com.itticket.consultation.service;

import com.itticket.consultation.api.*;
import org.springframework.http.MediaType;
import org.springframework.transaction.support.TransactionSynchronization;
import org.springframework.transaction.support.TransactionSynchronizationManager;
import org.springframework.web.multipart.MultipartFile;

import javax.imageio.ImageIO;
import javax.imageio.ImageReader;
import javax.imageio.stream.MemoryCacheImageInputStream;
import java.io.*;
import java.nio.file.*;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.*;

/** Local storage fallback. There is no malware scanner in this deployment. */
final class ConsultationAttachmentStorage {
    static final int MAX_BYTES = 20 * 1024 * 1024;
    private final Path root;

    ConsultationAttachmentStorage(String directory) {
        root = Path.of(directory).toAbsolutePath().normalize();
    }

    byte[] readUpload(MultipartFile file) {
        if (file == null || file.isEmpty() || file.getSize() > MAX_BYTES) throw invalidFile();
        try (InputStream in = file.getInputStream()) {
            byte[] bytes = in.readNBytes(MAX_BYTES + 1);
            if (bytes.length == 0 || bytes.length > MAX_BYTES) throw invalidFile();
            return bytes;
        } catch (IOException e) {
            throw invalidFile();
        }
    }

    String save(byte[] bytes) {
        String key = "consultation/" + UUID.randomUUID();
        try {
            Files.createDirectories(root);
            Path directory = root.resolve("consultation");
            Files.createDirectories(directory);
            Path target = safePath(key);
            Files.write(target, bytes, StandardOpenOption.CREATE_NEW);
            if (TransactionSynchronizationManager.isSynchronizationActive()) {
                TransactionSynchronizationManager.registerSynchronization(new TransactionSynchronization() {
                    @Override public void afterCompletion(int status) {
                        if (status != STATUS_COMMITTED) delete(key);
                    }
                });
            }
            return key;
        } catch (IOException e) {
            delete(key);
            throw new ApiException(ApiCode.INTERNAL_ERROR, "附件保存失败");
        }
    }

    byte[] read(String key) {
        try (InputStream in = Files.newInputStream(safePath(key), LinkOption.NOFOLLOW_LINKS)) {
            byte[] bytes = in.readNBytes(MAX_BYTES + 1);
            if (bytes.length == 0 || bytes.length > MAX_BYTES) throw ApiException.notFound();
            return bytes;
        } catch (IOException e) {
            throw ApiException.notFound();
        }
    }

    void deleteAfterCommit(String key) {
        if (TransactionSynchronizationManager.isSynchronizationActive()) {
            TransactionSynchronizationManager.registerSynchronization(new TransactionSynchronization() {
                @Override public void afterCommit() { delete(key); }
            });
        } else {
            delete(key);
        }
    }

    void delete(String key) {
        try { Files.deleteIfExists(safePath(key)); }
        catch (IOException | ApiException ignored) {
            // A cleanup failure may leave an unreferenced local blob; it must not reverse a committed DB operation.
        }
    }

    private Path safePath(String key) {
        if (key == null || !key.matches("consultation/[a-f0-9-]{36}")) throw ApiException.notFound();
        Path target = root.resolve(key).normalize();
        if (!target.startsWith(root) || Files.isSymbolicLink(root)
                || Files.isSymbolicLink(target.getParent()) || Files.isSymbolicLink(target)) {
            throw ApiException.notFound();
        }
        return target;
    }

    static String fileName(String original) {
        String name = original == null ? "attachment" : original.replace('\\', '/');
        name = name.substring(name.lastIndexOf('/') + 1).replaceAll("[\\p{Cntrl}]", "").strip();
        if (name.isBlank() || name.equals(".") || name.equals("..")) name = "attachment";
        return name.length() > 255 ? name.substring(name.length() - 255) : name;
    }

    static String hash(byte[] bytes) {
        try { return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(bytes)); }
        catch (NoSuchAlgorithmException e) { throw new IllegalStateException(e); }
    }

    static String contentType(byte[] bytes, String claimed) {
        String imageType = imageType(bytes);
        if (imageType != null) return imageType;
        try {
            MediaType type = MediaType.parseMediaType(claimed == null ? "application/octet-stream" : claimed);
            if (!type.isWildcardType() && !type.isWildcardSubtype() && !type.getType().equalsIgnoreCase("image")) {
                String normalized = type.getType().toLowerCase(Locale.ROOT) + "/" + type.getSubtype().toLowerCase(Locale.ROOT);
                if (normalized.length() <= 255 && normalized.matches("[a-z0-9!#$&^_.+-]+/[a-z0-9!#$&^_.+-]+")) return normalized;
            }
        } catch (IllegalArgumentException ignored) { }
        return "application/octet-stream";
    }

    private static String imageType(byte[] bytes) {
        try (var input = new MemoryCacheImageInputStream(new ByteArrayInputStream(bytes))) {
            Iterator<ImageReader> readers = ImageIO.getImageReaders(input);
            if (!readers.hasNext()) return null;
            ImageReader reader = readers.next();
            try {
                String type = switch (reader.getFormatName().toLowerCase(Locale.ROOT)) {
                    case "png" -> "image/png";
                    case "jpeg", "jpg" -> "image/jpeg";
                    case "gif" -> "image/gif";
                    case "bmp" -> "image/bmp";
                    default -> null;
                };
                if (type == null) return null;
                reader.setInput(input, true, true);
                long pixels = (long) reader.getWidth(0) * reader.getHeight(0);
                // Bound decoding memory; huge/unrecognizable images remain downloadable as ordinary files.
                if (pixels <= 0 || pixels > 16_000_000) return null;
                return reader.read(0) != null ? type : null;
            } finally { reader.dispose(); }
        } catch (IOException | RuntimeException e) { return null; }
    }

    private static ApiException invalidFile() {
        return ApiException.validation(List.of(FieldIssue.invalid("file", "文件不能为空、无法读取或超过 20MB")));
    }
}
