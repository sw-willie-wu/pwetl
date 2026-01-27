"""Command-line interface for pwetl."""
import argparse
import sys
from pathlib import Path
from pwetl.core.engine import ETLEngine


def cli_entry_point():
    """CLI 入口點。"""
    parser = argparse.ArgumentParser(
        prog='pwetl',
        description='pwetl - A flexible ETL framework based on Pathway',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
範例:
  # 基本執行
  pwetl --config config.yaml

  # 詳細模式
  pwetl --config config.yaml --verbose

  # 只驗證配置
  pwetl --config config.yaml --dry-run

  # 指定 .env 檔案
  pwetl --config config.yaml --env-file .env.production

更多資訊請參閱: https://github.com/yourusername/pwetl
        """,
    )

    # 必須參數
    parser.add_argument(
        '--config',
        required=True,
        type=str,
        help='配置檔案路徑（YAML 格式）',
    )

    # 可選參數
    parser.add_argument(
        '--verbose',
        '-v',
        action='store_true',
        help='顯示詳細輸出',
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='只驗證配置，不執行 ETL',
    )

    parser.add_argument(
        '--env-file',
        type=str,
        default=None,
        help='指定 .env 檔案路徑（預設: .env）',
    )

    parser.add_argument(
        '--version',
        action='version',
        version='pwetl 0.1.0',
        help='顯示版本資訊',
    )

    # 解析參數
    args = parser.parse_args()

    # 執行
    try:
        # 檢查配置檔案是否存在
        config_path = Path(args.config)
        if not config_path.exists():
            print(f"❌ 錯誤: 配置檔案不存在: {args.config}")
            sys.exit(1)

        # 建立 ETL Engine
        engine = ETLEngine(
            config_path=args.config,
            env_file=args.env_file,
            verbose=args.verbose,
        )

        # 執行或驗證
        if args.dry_run:
            engine.dry_run()
        else:
            engine.execute()

    except KeyboardInterrupt:
        print("\n\n⚠️  使用者中斷執行")
        sys.exit(130)

    except Exception as e:
        print(f"\n❌ 執行失敗: {e}")
        if args.verbose:
            import traceback
            print("\n詳細錯誤訊息:")
            traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    cli_entry_point()
