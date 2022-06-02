import base58
import json
import itertools

import near_api
from near_api import transactions

# Amount of gas attached by default 1e14.
DEFAULT_ATTACHED_GAS = 100_000_000_000_000


class TransactionError(Exception):
    pass


class ViewFunctionError(Exception):
    pass


class Account(object):

    def __init__(
            self,
            provider: 'near_api.providers.JsonProvider',
            signer: 'near_api.signer.Signer',
            account_id: str
    ):
        self._provider = provider
        self._signer = signer
        self._account_id = account_id
        self._account: dict = provider.get_account(account_id)
        self._access_key: dict = provider.get_access_key(account_id, self._signer.key_pair.encoded_public_key())

    def _sign_and_submit_tx(self, receiver_id: str, actions) -> dict:
        self._access_key["nonce"] += 1
        block_hash = self._provider.get_status()['sync_info']['latest_block_hash']
        block_hash = base58.b58decode(block_hash.encode('utf8'))
        serialized_tx = transactions.sign_and_serialize_transaction(
            receiver_id, self._access_key["nonce"], actions, block_hash, self._signer)
        result: dict = self._provider.send_tx_and_wait(serialized_tx, 10)
        for outcome in itertools.chain([result['transaction_outcome']], result['receipts_outcome']):
            for log in outcome['outcome']['logs']:
                print("Log:", log, flush=True)
        if 'Failure' in result['status']:
            raise TransactionError(result['status']['Failure'])
        return result
    
    def _sign_and_submit_tx_async(self, receiver_id: str, actions) -> str:
        """
        _sign_and_submit_tx_async
        
        sending in async not await method
        result gives a tx_hash to look at explorer
        https://docs.near.org/docs/api/rpc/transactions#send-transaction-async

        Args:
            receiver_id (str): account name receiving transaction results
            actions (_type_): list of transaction actions

        Returns:
            str: tx_hash of transaction
        """
        self._access_key["nonce"] += 1
        block_hash = self._provider.get_status()['sync_info']['latest_block_hash']
        block_hash = base58.b58decode(block_hash.encode('utf8'))
        serialized_tx = transactions.sign_and_serialize_transaction(
            receiver_id, self._access_key["nonce"], actions, block_hash, self._signer)
        result = self._provider.send_tx(serialized_tx)
        if (len(result) == 44):
            # ok test for now, bc tx_hash is 44 chars long
            raise TransactionError(f'Unable to sign and submit transaction. tx_hash is "{result}"')
        return result

    @property
    def account_id(self) -> str:
        return self._account_id

    @property
    def signer(self) -> 'near_api.signer.Signer':
        return self._signer

    @property
    def provider(self) -> 'near_api.providers.JsonProvider':
        return self._provider

    @property
    def access_key(self) -> dict:
        return self._access_key

    @property
    def state(self) -> dict:
        return self._account

    def fetch_state(self):
        """Fetch state for given account."""
        self._account = self.provider.get_account(self.account_id)

    def send_money(self, account_id: str, amount: int) -> str:
        """Sends funds to given account_id given amount."""
        return self._sign_and_submit_tx(account_id, [transactions.create_transfer_action(amount)])
    
    def send_money_async(self, account_id: str, amount: int) -> str:
        """Sends funds to given account_id given amount."""
        return self._sign_and_submit_tx_async(account_id, [transactions.create_transfer_action(amount)])

    def function_call(self, contract_id, method_name, args, gas=DEFAULT_ATTACHED_GAS, amount=0) -> str:
        """NEAR call method"""
        args = json.dumps(args).encode('utf8')
        return self._sign_and_submit_tx(contract_id,
                                        [transactions.create_function_call_action(method_name, args, gas, amount)])
    
    def function_call_async(self, contract_id, method_name, args, gas=DEFAULT_ATTACHED_GAS, amount=0) -> str:
        """NEAR call method"""
        args = json.dumps(args).encode('utf8')
        return self._sign_and_submit_tx_async(contract_id,
                                        [transactions.create_function_call_action(method_name, args, gas, amount)])

    def create_account(self, account_id, public_key, initial_balance) -> str:
        actions = [
            transactions.create_create_account_action(),
            transactions.create_full_access_key_action(public_key),
            transactions.create_transfer_action(initial_balance)]
        return self._sign_and_submit_tx(account_id, actions)
    
    def create_account_async(self, account_id, public_key, initial_balance) -> str:
        actions = [
            transactions.create_create_account_action(),
            transactions.create_full_access_key_action(public_key),
            transactions.create_transfer_action(initial_balance)]
        return self._sign_and_submit_tx_async(account_id, actions)

    def delete_account(self, beneficiary_id: str) -> str:
        return self._sign_and_submit_tx(self._account_id, [transactions.create_delete_account_action(beneficiary_id)])
    
    def delete_account_async(self, beneficiary_id: str) -> str:
        return self._sign_and_submit_tx_async(self._account_id, [transactions.create_delete_account_action(beneficiary_id)])
    
    def create_full_access_key(self, public_key) -> str:
        return self._sign_and_submit_tx(self._account_id, [transactions.create_full_access_key_action(public_key)])
    
    def create_full_access_key_async(self, public_key) -> str:
        return self._sign_and_submit_tx_async(self._account_id, [transactions.create_full_access_key_action(public_key)])
    
    def delete_access_key(self, public_key) -> str:
        return self._sign_and_submit_tx(self._account_id, [transactions.create_delete_access_key_action(public_key)])

    def delete_access_key_async(self, public_key) -> str:
        return self._sign_and_submit_tx_async(self._account_id, [transactions.create_delete_access_key_action(public_key)])

    def deploy_contract(self, contract_code) -> str:
        return self._sign_and_submit_tx(self._account_id, [transactions.create_deploy_contract_action(contract_code)])

    def deploy_contract_async(self, contract_code) -> str:
        return self._sign_and_submit_tx_async(self._account_id, [transactions.create_deploy_contract_action(contract_code)])

    def deploy_and_init_contract(self, contract_code, args, gas=DEFAULT_ATTACHED_GAS, 
                                 init_method_name="new") -> str:
        args = json.dumps(args).encode('utf8')
        actions = [     
            near_api.transactions.create_deploy_contract_action(contract_code),
            near_api.transactions.create_function_call_action(init_method_name, args, gas, 0)
        ]
        return self._sign_and_submit_tx(self._account_id, actions)

    def deploy_and_init_contract_async(self, contract_code, args, gas=DEFAULT_ATTACHED_GAS, 
                                 init_method_name="new") -> str:
        args = json.dumps(args).encode('utf8')
        actions = [     
            near_api.transactions.create_deploy_contract_action(contract_code),
            near_api.transactions.create_function_call_action(init_method_name, args, gas, 0)
        ]
        return self._sign_and_submit_tx_async(self._account_id, actions)
    
    def stake(self, public_key, amount) -> str:
        return self._sign_and_submit_tx(self._account_id, [transactions.create_staking_action(public_key, amount)])

    def stake_async(self, public_key, amount) -> str:
        return self._sign_and_submit_tx_async(self._account_id, [transactions.create_staking_action(public_key, amount)])

    def create_and_deploy_contract(self, contract_id, public_key, contract_code, initial_balance) -> str:
        actions = [
                      transactions.create_create_account_action(),
                      transactions.create_transfer_action(initial_balance),
                      transactions.create_deploy_contract_action(contract_code)
                  ] + ([transactions.create_full_access_key_action(public_key)] if public_key is not None else [])
        return self._sign_and_submit_tx(contract_id, actions)
    
    def create_and_deploy_contract_async(self, contract_id, public_key, contract_code, initial_balance) -> str:
        actions = [
                      transactions.create_create_account_action(),
                      transactions.create_transfer_action(initial_balance),
                      transactions.create_deploy_contract_action(contract_code)
                  ] + ([transactions.create_full_access_key_action(public_key)] if public_key is not None else [])
        return self._sign_and_submit_tx_async(contract_id, actions)

    def create_deploy_and_init_contract(self, contract_id, public_key, contract_code, initial_balance, args,
                                        gas=DEFAULT_ATTACHED_GAS, init_method_name="new") -> str:
        args = json.dumps(args).encode('utf8')
        actions = [
                      transactions.create_create_account_action(),
                      transactions.create_transfer_action(initial_balance),
                      transactions.create_deploy_contract_action(contract_code),
                      transactions.create_function_call_action(init_method_name, args, gas, 0)
                  ] + ([transactions.create_full_access_key_action(public_key)] if public_key is not None else [])
        return self._sign_and_submit_tx(contract_id, actions)

    def create_deploy_and_init_contract_async(self, contract_id, public_key, contract_code, initial_balance, args,
                                        gas=DEFAULT_ATTACHED_GAS, init_method_name="new") -> str:
        args = json.dumps(args).encode('utf8')
        actions = [
                      transactions.create_create_account_action(),
                      transactions.create_transfer_action(initial_balance),
                      transactions.create_deploy_contract_action(contract_code),
                      transactions.create_function_call_action(init_method_name, args, gas, 0)
                  ] + ([transactions.create_full_access_key_action(public_key)] if public_key is not None else [])
        return self._sign_and_submit_tx_async(contract_id, actions)

    def view_function(self, contract_id, method_name, args) -> dict:
        """NEAR view method"""
        result = self._provider.view_call(contract_id, method_name, json.dumps(args).encode('utf8'))
        if "error" in result:
            raise ViewFunctionError(result["error"])
        result["result"] = json.loads(''.join([chr(x) for x in result["result"]]))
        return result
