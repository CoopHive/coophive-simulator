use alloy::{
    network::{AnyNetwork, Ethereum, EthereumWallet},
    providers::{
        fillers::{
            BlobGasFiller, ChainIdFiller, FillProvider, GasFiller, JoinFill, NonceFiller,
            WalletFiller,
        },
        ProviderBuilder, RootProvider,
    },
    signers::local::PrivateKeySigner,
    transports::http::{Client, Http},
};
use alloy_provider::Identity;
use pyo3::{exceptions::PyValueError, PyErr};
use std::env;

use crate::py_val_err;

pub fn get_provider(
    private_key: String,
) -> Result<
    FillProvider<
        JoinFill<
            JoinFill<
                Identity,
                JoinFill<GasFiller, JoinFill<BlobGasFiller, JoinFill<NonceFiller, ChainIdFiller>>>,
            >,
            WalletFiller<EthereumWallet>,
        >,
        RootProvider<Http<Client>>,
        Http<Client>,
        Ethereum,
    >,
    pyo3::PyErr,
> {
    let signer: PrivateKeySigner = private_key
        .parse()
        .or_else(|_| py_val_err!("couldn't parse private_key as PrivateKeySigner"))?;

    println!("privkey: {}", private_key);
    println!("pubkey: {}", signer.address());

    let wallet = EthereumWallet::from(signer);
    let rpc_url = env::var("RPC_URL")
        .or_else(|_| py_val_err!("RPC_URL not set"))?
        .parse()
        .or_else(|_| py_val_err!("couldn't parse RPC_URL as a url"))?;

    let provider = ProviderBuilder::new()
        .with_recommended_fillers()
        .wallet(wallet)
        .on_http(rpc_url);

    Ok(provider)
}
