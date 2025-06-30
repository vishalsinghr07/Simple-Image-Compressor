import sys
import os
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QListWidget, QFileDialog, QProgressBar, QLabel, QMessageBox
)
from PyQt5.QtCore import QThread, pyqtSignal, Qt
from PIL import Image

class CompressionWorker(QThread):
    """
    A worker thread to handle the image compression process in the background,
    preventing the GUI from freezing.
    """
    progress_updated = pyqtSignal(int)
    status_updated = pyqtSignal(str)
    finished = pyqtSignal(int, float, float)

    def __init__(self, image_paths, output_dir):
        super().__init__()
        self.image_paths = image_paths
        self.output_dir = output_dir
        self.is_running = True

    def run(self):
        """Main execution method for the thread."""
        total_files = len(self.image_paths)
        compressed_count = 0
        original_size_total = 0
        compressed_size_total = 0

        for i, file_path in enumerate(self.image_paths):
            if not self.is_running:
                break

            self.status_updated.emit(f"Compressing: {os.path.basename(file_path)}")
            
            try:
                original_size = os.path.getsize(file_path) / 1024  # in KB
                original_size_total += original_size

                image = Image.open(file_path)
                
                # Strip EXIF data for JPEGs to reduce size
                if 'exif' in image.info:
                    del image.info['exif']
                
                # Prepare output path
                file_name = os.path.basename(file_path)
                output_path = os.path.join(self.output_dir, file_name)

                # Apply lossless or near-lossless compression
                if file_path.lower().endswith(('.jpg', '.jpeg')):
                    image.save(output_path, 'JPEG', quality=95, optimize=True)
                elif file_path.lower().endswith('.png'):
                    image.save(output_path, 'PNG', optimize=True, compress_level=9)
                else:
                    # For other formats, just save a copy
                    image.save(output_path)
                
                compressed_size = os.path.getsize(output_path) / 1024  # in KB
                compressed_size_total += compressed_size
                compressed_count += 1

            except Exception as e:
                self.status_updated.emit(f"Error compressing {os.path.basename(file_path)}: {e}")

            # Update progress
            progress_percent = int(((i + 1) / total_files) * 100)
            self.progress_updated.emit(progress_percent)

        self.finished.emit(compressed_count, original_size_total, compressed_size_total)

    def stop(self):
        """Stops the thread."""
        self.is_running = False

class ClarityCompressApp(QMainWindow):
    """Main application window."""
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ClarityCompress - Lossless Image Compressor")
        self.setGeometry(100, 100, 700, 500)
        
        self.image_files = []
        self.output_directory = ""

        # Main widget and layout
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)

        # --- UI Elements ---

        # 1. File Selection Buttons
        button_layout = QHBoxLayout()
        self.select_files_btn = QPushButton("Select Images")
        self.select_folder_btn = QPushButton("Select Folder")
        button_layout.addWidget(self.select_files_btn)
        button_layout.addWidget(self.select_folder_btn)
        self.main_layout.addLayout(button_layout)

        # 2. File List Display
        self.file_list_widget = QListWidget()
        self.main_layout.addWidget(self.file_list_widget)

        # 3. Save Location
        save_layout = QHBoxLayout()
        self.save_dir_label = QLabel("Save to: Not selected")
        self.save_dir_btn = QPushButton("Choose Save Location")
        save_layout.addWidget(self.save_dir_label)
        save_layout.addWidget(self.save_dir_btn)
        self.main_layout.addLayout(save_layout)

        # 4. Action Buttons
        action_layout = QHBoxLayout()
        self.compress_btn = QPushButton("Compress")
        self.clear_btn = QPushButton("Clear List")
        action_layout.addWidget(self.compress_btn)
        action_layout.addWidget(self.clear_btn)
        self.main_layout.addLayout(action_layout)

        # 5. Progress Bar and Status
        self.progress_bar = QProgressBar()
        self.status_label = QLabel("Ready. Select images or a folder to start.")
        self.main_layout.addWidget(self.progress_bar)
        self.main_layout.addWidget(self.status_label)

        # --- Connect Signals to Slots ---
        self.select_files_btn.clicked.connect(self.select_files)
        self.select_folder_btn.clicked.connect(self.select_folder)
        self.save_dir_btn.clicked.connect(self.select_output_directory)
        self.compress_btn.clicked.connect(self.start_compression)
        self.clear_btn.clicked.connect(self.clear_list)

    def select_files(self):
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Select Images",
            "",
            "Image Files (*.png *.jpg *.jpeg *.bmp);;All Files (*)"
        )
        if files:
            self.add_files_to_list(files)

    def select_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Folder")
        if folder:
            image_files = []
            for root, _, filenames in os.walk(folder):
                for filename in filenames:
                    if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp')):
                        image_files.append(os.path.join(root, filename))
            if image_files:
                self.add_files_to_list(image_files)
            else:
                QMessageBox.information(self, "No Images Found", "The selected folder contains no supported image files.")

    def add_files_to_list(self, files):
        for file in files:
            if file not in self.image_files:
                self.image_files.append(file)
                self.file_list_widget.addItem(os.path.basename(file))
        self.status_label.setText(f"{len(self.image_files)} image(s) selected.")

    def clear_list(self):
        self.image_files.clear()
        self.file_list_widget.clear()
        self.progress_bar.setValue(0)
        self.status_label.setText("Ready. Select images or a folder to start.")

    def select_output_directory(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Save Location")
        if folder:
            self.output_directory = folder
            self.save_dir_label.setText(f"Save to: {self.output_directory}")

    def start_compression(self):
        if not self.image_files:
            QMessageBox.warning(self, "No Images", "Please select images or a folder first.")
            return
        if not self.output_directory:
            QMessageBox.warning(self, "No Save Location", "Please choose a location to save the compressed images.")
            return

        self.compress_btn.setEnabled(False)
        self.clear_btn.setEnabled(False)
        
        # Start the worker thread
        self.worker = CompressionWorker(self.image_files, self.output_directory)
        self.worker.progress_updated.connect(self.update_progress)
        self.worker.status_updated.connect(self.update_status)
        self.worker.finished.connect(self.on_compression_finished)
        self.worker.start()

    def update_progress(self, value):
        self.progress_bar.setValue(value)

    def update_status(self, message):
        self.status_label.setText(message)

    def on_compression_finished(self, count, original_size, compressed_size):
        self.compress_btn.setEnabled(True)
        self.clear_btn.setEnabled(True)
        self.progress_bar.setValue(100)
        
        reduction_kb = original_size - compressed_size
        reduction_percent = (reduction_kb / original_size * 100) if original_size > 0 else 0
        
        summary_message = (
            f"Compression complete! {count} images compressed.\n\n"
            f"Original size: {original_size:.2f} KB\n"
            f"Compressed size: {compressed_size:.2f} KB\n"
            f"Total reduction: {reduction_kb:.2f} KB ({reduction_percent:.2f}%)"
        )
        
        self.status_label.setText(f"Finished. Compressed {count} images.")
        QMessageBox.information(self, "Success", summary_message)

    def closeEvent(self, event):
        """Ensure the worker thread is stopped when closing the app."""
        if hasattr(self, 'worker') and self.worker.isRunning():
            self.worker.stop()
            self.worker.wait() # Wait for the thread to finish
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    main_app = ClarityCompressApp()
    main_app.show()
    sys.exit(app.exec_())