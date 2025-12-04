import 'package:cloud_firestore/cloud_firestore.dart';

class TradeLog {
  final String id;
  final DateTime timestamp;
  final String type; // BUY, SELL, INFO, ERROR
  final String stockCode;
  final String stockName;
  final String message;
  final double? price;
  final int? quantity;
  final String? reason;

  TradeLog({
    required this.id,
    required this.timestamp,
    required this.type,
    required this.stockCode,
    required this.stockName,
    required this.message,
    this.price,
    this.quantity,
    this.reason,
  });

  factory TradeLog.fromFirestore(Map<String, dynamic> data, String id) {
    return TradeLog(
      id: id,
      timestamp: (data['timestamp'] as Timestamp).toDate(),
      type: data['type'] ?? 'INFO',
      stockCode: data['stockCode'] ?? '',
      stockName: data['stockName'] ?? '',
      message: data['message'] ?? '',
      price: data['price']?.toDouble(),
      quantity: data['quantity'],
      reason: data['reason'],
    );
  }
}