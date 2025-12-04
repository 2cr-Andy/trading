import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:intl/intl.dart';
import '../providers/market_data_provider.dart';
import '../models/trade_log.dart';
import '../theme/app_theme.dart';

class TradeLogPanel extends StatelessWidget {
  const TradeLogPanel({super.key});

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: Theme.of(context).colorScheme.surface.withOpacity(0.5),
              border: Border(
                bottom: BorderSide(
                  color: Theme.of(context).dividerColor,
                ),
              ),
            ),
            child: Row(
              children: [
                const Icon(Icons.terminal, size: 20),
                const SizedBox(width: 8),
                const Text(
                  '실시간 로그',
                  style: TextStyle(
                    fontSize: 16,
                    fontWeight: FontWeight.bold,
                  ),
                ),
                const Spacer(),
                // 필터 버튼들
                _buildFilterChip(context, 'ALL'),
                const SizedBox(width: 4),
                _buildFilterChip(context, 'BUY'),
                const SizedBox(width: 4),
                _buildFilterChip(context, 'SELL'),
                const SizedBox(width: 4),
                _buildFilterChip(context, 'ERROR'),
              ],
            ),
          ),

          Expanded(
            child: Consumer<MarketDataProvider>(
              builder: (context, provider, child) {
                if (provider.tradeLogs.isEmpty) {
                  return const Center(
                    child: Text(
                      '거래 로그가 없습니다',
                      style: TextStyle(color: Colors.white54),
                    ),
                  );
                }

                return Container(
                  color: Colors.black.withOpacity(0.3),
                  child: ListView.builder(
                    padding: const EdgeInsets.all(8),
                    itemCount: provider.tradeLogs.length,
                    reverse: true,
                    itemBuilder: (context, index) {
                      final log = provider.tradeLogs[provider.tradeLogs.length - 1 - index];
                      return _buildLogEntry(log);
                    },
                  ),
                );
              },
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildFilterChip(BuildContext context, String label) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
      decoration: BoxDecoration(
        color: _getLogTypeColor(label).withOpacity(0.2),
        borderRadius: BorderRadius.circular(4),
      ),
      child: Text(
        label,
        style: TextStyle(
          fontSize: 11,
          color: _getLogTypeColor(label),
        ),
      ),
    );
  }

  Widget _buildLogEntry(TradeLog log) {
    final timeFormat = DateFormat('HH:mm:ss');
    final typeColor = _getLogTypeColor(log.type);

    return Container(
      margin: const EdgeInsets.only(bottom: 4),
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 6),
      decoration: BoxDecoration(
        color: Colors.black.withOpacity(0.3),
        border: Border(
          left: BorderSide(
            color: typeColor,
            width: 2,
          ),
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // 시간과 타입
          Row(
            children: [
              Text(
                '[${timeFormat.format(log.timestamp)}]',
                style: const TextStyle(
                  fontSize: 12,
                  color: Colors.white54,
                  fontFamily: 'monospace',
                ),
              ),
              const SizedBox(width: 8),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 1),
                decoration: BoxDecoration(
                  color: typeColor.withOpacity(0.2),
                  borderRadius: BorderRadius.circular(3),
                ),
                child: Text(
                  log.type,
                  style: TextStyle(
                    fontSize: 11,
                    color: typeColor,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ),
              const SizedBox(width: 8),
              if (log.stockName.isNotEmpty)
                Text(
                  log.stockName,
                  style: const TextStyle(
                    fontSize: 12,
                    fontWeight: FontWeight.bold,
                  ),
                ),
            ],
          ),

          const SizedBox(height: 4),

          // 메시지
          Text(
            log.message,
            style: const TextStyle(
              fontSize: 13,
              fontFamily: 'monospace',
              height: 1.4,
            ),
          ),

          // 추가 정보 (가격, 수량)
          if (log.price != null && log.quantity != null) ...[
            const SizedBox(height: 4),
            Text(
              '가격: ₩${NumberFormat('#,###').format(log.price)} | 수량: ${log.quantity}주',
              style: TextStyle(
                fontSize: 11,
                color: Colors.white.withOpacity(0.6),
                fontFamily: 'monospace',
              ),
            ),
          ],

          // 이유
          if (log.reason != null) ...[
            const SizedBox(height: 4),
            Text(
              '➤ ${log.reason}',
              style: TextStyle(
                fontSize: 12,
                color: AppTheme.successColor.withOpacity(0.8),
                fontStyle: FontStyle.italic,
              ),
            ),
          ],
        ],
      ),
    );
  }

  Color _getLogTypeColor(String type) {
    switch (type.toUpperCase()) {
      case 'BUY':
        return AppTheme.successColor;
      case 'SELL':
        return Colors.orange;
      case 'ERROR':
        return AppTheme.upColor;
      case 'INFO':
        return Colors.blue;
      case 'ALL':
        return Colors.white70;
      default:
        return Colors.white54;
    }
  }
}