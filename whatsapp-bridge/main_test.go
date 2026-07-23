package main

import (
	"testing"
	"time"

	waProto "go.mau.fi/whatsmeow/binary/proto"
	"google.golang.org/protobuf/proto"
)

func TestExtractDirectPathFromURL(t *testing.T) {
	tests := []struct {
		name string
		url  string
		want string
	}{
		{
			name: "typical media url with query params",
			url:  "https://mmg.whatsapp.net/v/t62.7118-24/13812002_698058036224062_3424455886509161511_n.enc?ccb=11-4&oh=abc123&oe=def456",
			want: "/v/t62.7118-24/13812002_698058036224062_3424455886509161511_n.enc",
		},
		{
			name: "url without query params",
			url:  "https://mmg.whatsapp.net/v/t62.7118-24/some_file.enc",
			want: "/v/t62.7118-24/some_file.enc",
		},
		{
			name: "malformed url falls back to original",
			url:  "not-a-valid-whatsapp-url",
			want: "not-a-valid-whatsapp-url",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got := extractDirectPathFromURL(tt.url)
			if got != tt.want {
				t.Errorf("extractDirectPathFromURL(%q) = %q, want %q", tt.url, got, tt.want)
			}
		})
	}
}
func TestExtractMediaInfo_Image(t *testing.T) {
	msg := &waProto.Message{
		ImageMessage: &waProto.ImageMessage{
			URL:           proto.String("https://mmg.whatsapp.net/v/t62.7118-24/file.enc?oh=abc&oe=def"),
			DirectPath:    proto.String("/v/t62.7118-24/file.enc"),
			MediaKey:      []byte{1, 2, 3},
			FileSHA256:    []byte{4, 5, 6},
			FileEncSHA256: []byte{7, 8, 9},
			FileLength:    proto.Uint64(12345),
		},
	}

	mediaType, filename, url, directPath, mediaKey, fileSHA256, fileEncSHA256, fileLength := extractMediaInfo(msg)

	if mediaType != "image" {
		t.Errorf("mediaType = %q, want %q", mediaType, "image")
	}
	if directPath != "/v/t62.7118-24/file.enc" {
		t.Errorf("directPath = %q, want %q", directPath, "/v/t62.7118-24/file.enc")
	}
	if url != "https://mmg.whatsapp.net/v/t62.7118-24/file.enc?oh=abc&oe=def" {
		t.Errorf("url mismatch: %q", url)
	}
	if fileLength != 12345 {
		t.Errorf("fileLength = %d, want 12345", fileLength)
	}
	if len(mediaKey) != 3 || len(fileSHA256) != 3 || len(fileEncSHA256) != 3 {
		t.Errorf("byte slices not passed through correctly")
	}
	if filename == "" {
		t.Errorf("filename should not be empty")
	}
}

func TestExtractMediaInfo_NoMedia(t *testing.T) {
	msg := &waProto.Message{
		Conversation: proto.String("just a text message"),
	}

	mediaType, _, _, directPath, _, _, _, _ := extractMediaInfo(msg)

	if mediaType != "" {
		t.Errorf("mediaType = %q, want empty for text-only message", mediaType)
	}
	if directPath != "" {
		t.Errorf("directPath = %q, want empty for text-only message", directPath)
	}
}
func TestStoreAndGetMediaInfo_DirectPath(t *testing.T) {
	dbPath := t.TempDir() + "/test_messages.db"
	store, err := NewMessageStore(dbPath)
	if err != nil {
		t.Fatalf("failed to create test message store: %v", err)
	}
	defer store.Close()

	err = store.StoreMessage(
		"MSG123",
		"120363425169802602@g.us",
		"266837862400014",
		"",
		time.Now(),
		false,
		"image",
		"image_test.jpg",
		"https://mmg.whatsapp.net/v/t62.7118-24/file.enc?oh=abc&oe=def",
		"/v/t62.7118-24/file.enc",
		[]byte{1, 2, 3},
		[]byte{4, 5, 6},
		[]byte{7, 8, 9},
		12345,
	)
	if err != nil {
		t.Fatalf("StoreMessage failed: %v", err)
	}

	mediaType, filename, url, directPath, mediaKey, fileSHA256, fileEncSHA256, fileLength, err :=
		store.GetMediaInfo("MSG123", "120363425169802602@g.us")
	if err != nil {
		t.Fatalf("GetMediaInfo failed: %v", err)
	}

	if mediaType != "image" {
		t.Errorf("mediaType = %q, want %q", mediaType, "image")
	}
	if filename != "image_test.jpg" {
		t.Errorf("filename = %q, want %q", filename, "image_test.jpg")
	}
	if directPath != "/v/t62.7118-24/file.enc" {
		t.Errorf("directPath = %q, want %q (this is the field we added in Passo 5)", directPath, "/v/t62.7118-24/file.enc")
	}
	if url == "" {
		t.Errorf("url should not be empty")
	}
	if fileLength != 12345 {
		t.Errorf("fileLength = %d, want 12345", fileLength)
	}
	if len(mediaKey) != 3 || len(fileSHA256) != 3 || len(fileEncSHA256) != 3 {
		t.Errorf("byte slices not round-tripped correctly")
	}
}
