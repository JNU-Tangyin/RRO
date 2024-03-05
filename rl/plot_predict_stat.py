import pandas as pd
import numpy as np
from plotnine import ggplot, aes, geom_bar, element_blank, labs, scale_fill_gradient
from plotnine_prism import theme_prism
import json
import random

work_type_df = pd.read_excel('../datasets/excel/TYPE_WORK.xlsx')
container_type_df = pd.read_excel('../datasets/excel/CONTAINER_TYPE.xlsx')
ship_company_df = pd.read_excel('../datasets/excel/CNTR_ADMIN_CODE.xlsx')
ship_company_df = ship_company_df.sort_values(by='AVG_DIFF')
payment_df = pd.read_excel('../datasets/excel/PAYMENT_CODE.xlsx')
payment_df = payment_df.sort_values(by='AVG_DIFF')
cargo_df = pd.read_excel('../datasets/excel/GOODS_IN_CHINESE.xlsx')
cargo_df = cargo_df.sort_values(by='AVG_DIFF')

work_type_df['TYPE_WORK'] = pd.Categorical(work_type_df['TYPE_WORK'],
                                           categories=list(work_type_df['TYPE_WORK']),
                                           ordered=True)

container_type_df['CONTAINER_TYPE_STR'] = pd.Categorical(container_type_df['CONTAINER_TYPE_STR'],
                                                         categories=list(container_type_df['CONTAINER_TYPE_STR']),
                                                         ordered=True)

ship_company_df['CNTR_ADMIN_CODE'] = pd.Categorical(ship_company_df['CNTR_ADMIN_CODE'],
                                                    categories=list(ship_company_df['CNTR_ADMIN_CODE']),
                                                    ordered=True)

payment_df['PAYMENT_CODE'] = pd.Categorical(payment_df['PAYMENT_CODE'],
                                            categories=list(payment_df['PAYMENT_CODE']),
                                            ordered=True)

cargo_df['GOODS_IN_CHINESE'] = pd.Categorical(cargo_df['GOODS_IN_CHINESE'],
                                              categories=list(cargo_df['GOODS_IN_CHINESE']), ordered=True)

plot = (ggplot()
        + geom_bar(work_type_df, aes(x='TYPE_WORK', y='AVG_DIFF', fill='AVG_DIFF'), stat='identity')
        + labs(x='Operation type', y='Stacking days')
        + scale_fill_gradient(low='#fe3232', high='#fedc32')
        + theme_prism()
        )

ctn_plot = (ggplot()
            + geom_bar(container_type_df,
                       aes(x='CONTAINER_TYPE_STR', y='AVG_DIFF', fill='AVG_DIFF'),
                       stat='identity')
            + labs(x='Container size', y='Stacking days')
            + scale_fill_gradient(low='#fe3232', high='#fedc32')
            + theme_prism()
            )

sc_plot = (ggplot()
           + geom_bar(ship_company_df,
                      aes(x='CNTR_ADMIN_CODE', y='AVG_DIFF', fill='AVG_DIFF'),
                      stat='identity')
           + labs(x='Shipping company', y='Stacking days')
           + scale_fill_gradient(low='#fe3232', high='#fedc32')
           + theme_prism(axis_text_x=element_blank())
           )

payment_plot = (ggplot()
                + geom_bar(payment_df,
                           aes(x='PAYMENT_CODE', y='AVG_DIFF', fill='AVG_DIFF'),
                           stat='identity')
                + labs(x='Owner', y='Stacking days')
                + scale_fill_gradient(low='#fe3232', high='#fedc32')
                + theme_prism(axis_text_x=element_blank())
                )

cargo_plot = (ggplot()
              + geom_bar(cargo_df,
                         aes(x='GOODS_IN_CHINESE', y='AVG_DIFF', fill='AVG_DIFF'),
                         stat='identity')
              + labs(x='Cargo', y='Stacking days')
              + scale_fill_gradient(low='#fe3232', high='#fedc32')
              + theme_prism(axis_text_x=element_blank())
              )

plot.save('../figures/rl/stacking_days_by_work_type.png')
ctn_plot.save('../figures/rl/stacking_days_by_container_type.png')
sc_plot.save('../figures/rl/stacking_days_by_shipping_company.png')
payment_plot.save('../figures/rl/stacking_days_by_payment.png')
cargo_plot.save('../figures/rl/stacking_days_by_cargo.png')