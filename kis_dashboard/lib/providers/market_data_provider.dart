import 'package:flutter/material.dart';
import 'package:cloud_firestore/cloud_firestore.dart';
import '../models/stock_item.dart';
import '../models/portfolio_item.dart';
import '../models/trade_log.dart';

class MarketDataProvider extends ChangeNotifier {
  final FirebaseFirestore _firestore = FirebaseFirestore.instance;

  // 봇 상태
  bool _botRunning = false;
  DateTime? _lastHeartbeat;

  // 계좌 정보
  double _totalAssets = 0;
  double _totalCash = 0;
  double _todayPnL = 0;
  double _todayPnLPercent = 0;

  // 감시 종목 리스트
  List<StockItem> _watchlist = [];

  // 포트폴리오
  List<PortfolioItem> _portfolio = [];

  // 거래 로그
  List<TradeLog> _tradeLogs = [];

  // Getters
  bool get botRunning => _botRunning;
  DateTime? get lastHeartbeat => _lastHeartbeat;
  double get totalAssets => _totalAssets;
  double get totalCash => _totalCash;
  double get todayPnL => _todayPnL;
  double get todayPnLPercent => _todayPnLPercent;
  List<StockItem> get watchlist => _watchlist;
  List<PortfolioItem> get portfolio => _portfolio;
  List<TradeLog> get tradeLogs => _tradeLogs;

  MarketDataProvider() {
    _initializeStreams();
  }

  void _initializeStreams() {
    // 봇 상태 스트림
    _firestore.collection('bot_status').doc('main').snapshots().listen((snapshot) {
      if (snapshot.exists) {
        final data = snapshot.data()!;
        _botRunning = data['running'] ?? false;
        _lastHeartbeat = (data['lastHeartbeat'] as Timestamp?)?.toDate();
        notifyListeners();
      }
    });

    // 계좌 정보 스트림
    _firestore.collection('account').doc('summary').snapshots().listen((snapshot) {
      if (snapshot.exists) {
        final data = snapshot.data()!;
        _totalAssets = (data['totalAssets'] ?? 0).toDouble();
        _totalCash = (data['totalCash'] ?? 0).toDouble();
        _todayPnL = (data['todayPnL'] ?? 0).toDouble();
        _todayPnLPercent = (data['todayPnLPercent'] ?? 0).toDouble();
        notifyListeners();
      }
    });

    // 감시 종목 스트림 - market_scan의 latest 문서에서 stocks 배열 읽기
    _firestore.collection('market_scan')
        .doc('latest')
        .snapshots()
        .listen((snapshot) {
      if (snapshot.exists && snapshot.data() != null) {
        final data = snapshot.data()!;
        final stocksList = data['stocks'] as List<dynamic>? ?? [];
        _watchlist = stocksList
            .map((stockData) => StockItem.fromMarketScan(stockData))
            .toList();
        notifyListeners();
      }
    });

    // 포트폴리오 스트림
    _firestore.collection('portfolio')
        .snapshots()
        .listen((snapshot) {
      _portfolio = snapshot.docs
          .map((doc) => PortfolioItem.fromFirestore(doc.data(), doc.id))
          .toList();
      notifyListeners();
    });

    // 거래 로그 스트림 (최근 50개)
    _firestore.collection('trade_logs')
        .orderBy('timestamp', descending: true)
        .limit(50)
        .snapshots()
        .listen((snapshot) {
      _tradeLogs = snapshot.docs
          .map((doc) => TradeLog.fromFirestore(doc.data(), doc.id))
          .toList();
      notifyListeners();
    });
  }

  // 봇 시작/중지
  Future<void> toggleBot() async {
    await _firestore.collection('bot_status').doc('main').update({
      'running': !_botRunning,
      'lastUpdate': FieldValue.serverTimestamp(),
    });
  }

  // 전량 매도 (패닉 버튼)
  Future<void> panicSell() async {
    await _firestore.collection('commands').add({
      'type': 'PANIC_SELL',
      'timestamp': FieldValue.serverTimestamp(),
      'status': 'pending',
    });
  }

  // 특정 종목 수동 매도
  Future<void> manualSell(String stockCode) async {
    await _firestore.collection('commands').add({
      'type': 'MANUAL_SELL',
      'stockCode': stockCode,
      'timestamp': FieldValue.serverTimestamp(),
      'status': 'pending',
    });
  }
}