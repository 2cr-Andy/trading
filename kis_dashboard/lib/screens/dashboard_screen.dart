import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/market_data_provider.dart';
import '../widgets/header_widget.dart';
import '../widgets/watchlist_panel.dart';
import '../widgets/portfolio_panel.dart';
import '../widgets/trade_log_panel.dart';
import '../theme/app_theme.dart';

class DashboardScreen extends StatelessWidget {
  const DashboardScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Column(
        children: [
          // 상단 헤더 (Global Status)
          const HeaderWidget(),

          // 메인 컨텐츠 영역
          Expanded(
            child: Row(
              children: [
                // 좌측: 감시 종목 리스트 (30%)
                Expanded(
                  flex: 3,
                  child: Container(
                    margin: const EdgeInsets.all(8),
                    child: const WatchlistPanel(),
                  ),
                ),

                // 중앙: 포트폴리오 (40%)
                Expanded(
                  flex: 4,
                  child: Container(
                    margin: const EdgeInsets.symmetric(vertical: 8),
                    child: const PortfolioPanel(),
                  ),
                ),

                // 우측: 실시간 로그 (30%)
                Expanded(
                  flex: 3,
                  child: Container(
                    margin: const EdgeInsets.all(8),
                    child: const TradeLogPanel(),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}