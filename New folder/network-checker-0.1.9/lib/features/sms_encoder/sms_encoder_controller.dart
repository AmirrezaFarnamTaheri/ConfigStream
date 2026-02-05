import 'package:flutter/foundation.dart';
import 'package:flutter/services.dart';

/// SMS Encoder/Decoder Controller
/// Maps English letters and special characters to Persian letters
class SmsEncoderController extends ChangeNotifier {
  String _inputText = '';
  String _encodedText = '';
  String _decodedText = '';

  // Mapping: English letters (a-z) → Persian letters
  // Plus 6 special characters: " : / @ # .
  static const Map<String, String> _encodeMap = {
    // English letters a-z (26 letters)
    'a': 'ا',
    'b': 'ب',
    'c': 'پ',
    'd': 'ت',
    'e': 'ث',
    'f': 'ج',
    'g': 'چ',
    'h': 'ح',
    'i': 'خ',
    'j': 'د',
    'k': 'ذ',
    'l': 'ر',
    'm': 'ز',
    'n': 'ژ',
    'o': 'س',
    'p': 'ش',
    'q': 'ص',
    'r': 'ض',
    's': 'ط',
    't': 'ظ',
    'u': 'ع',
    'v': 'غ',
    'w': 'ف',
    'x': 'ق',
    'y': 'ک',
    'z': 'گ',
    // Uppercase letters map to same Persian letters
    'A': 'ا',
    'B': 'ب',
    'C': 'پ',
    'D': 'ت',
    'E': 'ث',
    'F': 'ج',
    'G': 'چ',
    'H': 'ح',
    'I': 'خ',
    'J': 'د',
    'K': 'ذ',
    'L': 'ر',
    'M': 'ز',
    'N': 'ژ',
    'O': 'س',
    'P': 'ش',
    'Q': 'ص',
    'R': 'ض',
    'S': 'ط',
    'T': 'ظ',
    'U': 'ع',
    'V': 'غ',
    'W': 'ف',
    'X': 'ق',
    'Y': 'ک',
    'Z': 'گ',
    // Special characters (remaining 6 Persian letters)
    '"': 'ل',
    ':': 'م',
    '/': 'ن',
    '@': 'و',
    '#': 'ه',
    '.': 'ی',
    // Other special characters
    '&': '!',
    '%': '،',
    // Numbers (English → Persian)
    '0': '۰',
    '1': '۱',
    '2': '۲',
    '3': '۳',
    '4': '۴',
    '5': '۵',
    '6': '۶',
    '7': '۷',
    '8': '۸',
    '9': '۹',
  };

  // Reverse mapping for decoding (prefers lowercase for letters)
  static final Map<String, String> _decodeMapFixed = () {
    final map = <String, String>{};
    for (final entry in _encodeMap.entries) {
      final persian = entry.value;
      final english = entry.key;
      // Only add if not already in map (keeps first occurrence which is lowercase)
      if (!map.containsKey(persian)) {
        map[persian] = english.toLowerCase();
      }
    }
    // Override with special characters (they don't have case)
    map['ل'] = '"';
    map['م'] = ':';
    map['ن'] = '/';
    map['و'] = '@';
    map['ه'] = '#';
    map['ی'] = '.';
    map['،'] = '%';
    // Other special characters
    map['!'] = '&';
    // Numbers (Persian → English)
    map['۰'] = '0';
    map['۱'] = '1';
    map['۲'] = '2';
    map['۳'] = '3';
    map['۴'] = '4';
    map['۵'] = '5';
    map['۶'] = '6';
    map['۷'] = '7';
    map['۸'] = '8';
    map['۹'] = '9';
    return map;
  }();

  // Getters
  String get inputText => _inputText;
  String get encodedText => _encodedText;
  String get decodedText => _decodedText;

  /// Sets the input text for encoding and automatically encodes it
  void setInputForEncoding(String input) {
    _inputText = input;
    _encodedText = _encode(input);
    notifyListeners();
  }

  /// Sets the input text for decoding and automatically decodes it
  void setInputForDecoding(String input) {
    _inputText = input;
    _decodedText = _decode(input);
    notifyListeners();
  }

  /// Encodes English text to Persian characters
  String _encode(String input) {
    final buffer = StringBuffer();
    final lowerInput = input.toLowerCase();
    for (int i = 0; i < lowerInput.length; i++) {
      final char = lowerInput[i];
      buffer.write(_encodeMap[char] ?? char);
    }
    return buffer.toString();
  }

  /// Decodes Persian characters back to English text
  String _decode(String input) {
    final buffer = StringBuffer();
    // Persian characters can be multi-byte, iterate by runes
    for (final rune in input.runes) {
      final char = String.fromCharCode(rune);
      buffer.write(_decodeMapFixed[char] ?? char);
    }
    return buffer.toString();
  }

  /// Copies encoded text to clipboard
  Future<void> copyEncodedToClipboard() async {
    if (_encodedText.isNotEmpty) {
      await Clipboard.setData(ClipboardData(text: _encodedText));
    }
  }

  /// Copies decoded text to clipboard
  Future<void> copyDecodedToClipboard() async {
    if (_decodedText.isNotEmpty) {
      await Clipboard.setData(ClipboardData(text: _decodedText));
    }
  }

  /// Clears all text
  void clear() {
    _inputText = '';
    _encodedText = '';
    _decodedText = '';
    notifyListeners();
  }
}

