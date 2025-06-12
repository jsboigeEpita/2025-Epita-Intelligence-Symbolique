/**
 * Whisper WebUI API Client using @gradio/client
 * For the doc and test the UI: https://whisper-webui.myia.io/?view=api
 * 
 * Installation: npm install @gradio/client
 */

import { Client, handle_file } from "@gradio/client";

class WhisperApiClient {
  constructor(baseUrl = "https://whisper-webui.myia.io/", username, password, apiKey) {
    this.baseUrl = baseUrl;
    this.username = username;
    this.password = password;
    this.apiKey = apiKey;
    this.client = null;
  }

  async connect() {
    if (!this.client) {
      console.log('Credentials:', this.username, this.password, this.apiKey);
      this.client = await Client.connect(this.baseUrl, {
        auth: [this.username, this.password]
      });
    }
    return this.client;
  }

  async transcribeYouTube(youtubeLink, options = {}) {
    const defaultOptions = {
      file_format: "txt",
      add_timestamp: false,
      progress: "large-v3-turbo", // model
      param_4: "english" || options.param_4, // language
      param_5: false, // use_auth_token
      param_6: 5, // chunk_length
      param_7: -1, // stride_length_s
      param_8: 0.6, // max_new_tokens
      param_9: "float16", // dtype
      param_10: 5, // batch_size
      param_11: 1, // assistant_model
      param_12: true, // use_bettertransformer
      param_13: 0.5, // flash_attention_2
      param_14: "Hello!!", // preprocess_text
      param_15: 0, // postprocess_text
      param_16: 2.4, // temperature
      param_17: 1, // compression_ratio_threshold
      param_18: 1, // log_prob_threshold
      param_19: 0, // no_speech_threshold
      param_20: "Hello!!", // initial_prompt
      param_21: true, // suppress_tokens
      param_22: "[-1]", // suppress_numerals
      param_23: 1, // max_initial_timestamp
      param_24: false, // word_timestamps
      param_25: "'\"¿([{-", // prepend_punctuations
      param_26: "'.。,，!！?？:：\")]}、", // append_punctuations
      param_27: 3, // max_line_width
      param_28: 30, // max_line_count
      param_29: 3, // max_words_per_line
      param_30: "Hello!!", // highlight_words
      param_31: 0.5, // segment_resolution
      param_32: 1, // fonts_size
      param_33: 24, // fonts_color
      param_34: true, // karaoke
      param_35: false, // embed_subs
      param_36: 0.5, // similarity_threshold
      param_37: 250, // min_word_dur
      param_38: 9999, // only_voice_freq
      param_39: 1000, // min_words_per_segment
      param_40: 2000, // min_words_per_segment_threshold
      param_41: false, // time_sync_adjustment
      param_42: "cuda", // device
      param_43: this.apiKey, // hugging_face_token
      param_44: true, // use_cache
      param_45: false, // delete_cache
      param_46: "UVR-MDX-NET-Inst_HQ_4", // uvr_model
      param_47: "cuda", // uvr_device
      param_48: 256, // uvr_segment_size
      param_49: false, // uvr_save_file
      param_50: true // bgm_separation
    };

    const finalOptions = {
      youtube_link: youtubeLink,
      ...defaultOptions, ...options
    };

    try {
      const client = await this.connect();
      const result = await client.predict("/transcribe_youtube", finalOptions);
      return this.processResult(result);

    } catch (error) {
      console.error('Error calling Whisper API:', error);
      throw error;
    }
  }

  async transcribeFile(file, options = {}) {
    if (!(file instanceof File)) {
      console.error('Invalid input to transcribeFile. Expected a File object, but got:', file);
      throw new Error('Invalid file object provided. Please select a file to upload.');
    }
    console.log('Processing file:', file.name, 'Type:', file.type);
    console.log('Full file object:', file);
    try {
      const client = await this.connect();
      console.log('Uploading file to Gradio server...');
      const arr = [file];
      console.log("File is array ?", Array.isArray(arr));
      console.log("File length:", arr.length);

      const uploadResponses = await client.upload_files("speech-to-text\\frontend\\test_files\\test1.mp3", arr);

      console.log('File uploaded successfully. Server response:', uploadedFile);

      const uploadedFile = uploadResponses[0];

      // Check if the server's response includes the original filename.
      // If not, the file type check will fail. We add it back manually if it's missing.
      if (uploadedFile && !uploadedFile.orig_name) {
        console.warn("The server's file object is missing 'orig_name'. Manually adding it to prevent file type errors.");
        uploadedFile.orig_name = file.name;
      }

      const parameters = {
        files: [uploadedFile], // Use the object returned by the upload method
        input_folder_path: "",
        include_subdirectory: false,
        save_same_dir: false,
        file_format: options.file_format || "txt",
        add_timestamp: options.add_timestamp || false,
        progress: options.model || "base",
        param_7: options.language || "english",
      };

      console.log('Sending prediction request with parameters:', parameters);
      const result = await client.predict("/transcribe_file", parameters);

      console.log('Raw result from Gradio:', result);
      return this.processResult(result);

    } catch (error) {
      console.error('An error occurred during transcription:', error);

      if (error.message && error.message.includes('401')) {
        throw new Error('Authentication failed. Please check your username and password.');
      }
      throw new Error(`Transcription failed: ${error.message}`);
    }
  }

  // Test method for transcribing a file using the Gradio client 
  async transcribeFileTest(file, options = {}) {
    // const fileRef = handle_file(file);
    const fileRef = {
      meta: { _type: 'gradio.FileData' },
      orig_name: file.name,
      path: URL.createObjectURL(file),
      url: URL.createObjectURL(file)
    };
    console.log('File reference:', fileRef);

    const payload = {
      files: [fileRef], // Must be an array
      file_format: "txt", // Output format
      // progress: "base", // Use the simplest model possible
      // param_4: "english", // Auto-detect language
    };

    try {
      const client = await this.connect();
      const result = await client.predict("/transcribe_file", payload);
      URL.revokeObjectURL(fileRef.path);
      URL.revokeObjectURL(fileRef.url);
      return this.processResult(result);
    } catch (error) {
      console.error('Error in transcribeFileTest:', error);
      throw new Error(`Transcription failed: ${error.message}`);
    }
  }

  // Debugging method to get Gradio interface info
  async debugGradioInterface() {
    try {
      const client = await this.connect();
      console.log('Gradio client connected successfully');

      // Get the interface info to understand expected parameters
      const interfaceInfo = await client.view_api();
      console.log('Gradio interface info:', interfaceInfo);

      // Look for the transcribe_file endpoint specifically
      const transcribeEndpoint = interfaceInfo.named_endpoints['/transcribe_file'];
      if (transcribeEndpoint) {
        console.log('Transcribe endpoint details:', transcribeEndpoint);
        console.log('Expected parameters:', transcribeEndpoint.parameters);
        console.log('Expected returns:', transcribeEndpoint.returns);
      }

      return interfaceInfo;
    } catch (error) {
      console.error('Error getting Gradio interface info:', error);
      throw error;
    }
  }

  // Process the result from the Whisper API
  processResult(result) {
    if (result && result.data && result.data[0]) {
      const transcription = result.data[0];
      const lines = transcription.split('\n').filter(line => line.trim() !== '');

      return {
        success: true,
        transcription: transcription,
        lines: lines,
        raw: result
      };
    }

    return {
      success: false,
      error: 'No transcription data received',
      raw: result
    };
  }

  async disconnect() {
    if (this.client) {
      await this.client.close();
      this.client = null;
    }
  }
}

export default WhisperApiClient;